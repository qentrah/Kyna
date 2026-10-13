#include "kyna/execution/tree_walk_engine.hpp"
#include "kyna/parsing/recursive_descent_parser.hpp"
#include "kyna/semantics/program_validation.hpp"
#include "kyna/stdlib/standard_library_catalog.hpp"
#include <cassert>

int main() {
  // A recursive function owns its defining environment; session teardown must
  // break the environment/function cycle, including nested callback closures.
  std::weak_ptr<kyna::Environment> releasedGlobals;
  std::weak_ptr<kyna::Environment> releasedClosure;
  std::weak_ptr<kyna::Function> releasedFunction;
  {
    kyna::Interpreter session;
    session.execute(kyna::Parser(kyna::lex(
        "fn factory(): any { fn callback(): void { return; } return callback; }"
        "var saved = factory();")).parse());
    releasedGlobals = session.globals();
    const auto callback = std::get<kyna::FunctionPtr>(session.globals()->get("saved").value.data);
    releasedFunction = callback;
    releasedClosure = callback->closure;
  }
  assert(releasedGlobals.expired());
  assert(releasedFunction.expired());
  assert(releasedClosure.expired());

  auto program =
      kyna::Parser(kyna::lex("class Node { public next: Node?; }"
                             "fn make(): void { var n = new Node(); n.next = n; return; }"
                             "loop (var i = 0; i < 300; i = i + 1) { make(); }"))
          .parse();
  assert(kyna::validate(program).empty());
  kyna::Interpreter interpreter(kyna::productionRuntimeCapabilities(),
                                kyna::installStandardLibrary);
  auto baselineObjects = interpreter.heap().live();
  interpreter.heap().setThreshold(1);
  interpreter.execute(program);
  assert(interpreter.heap().collections() > 0);
  assert(interpreter.heap().live() == baselineObjects);

  kyna::Heap isolatedHeap;
  {
    auto roots = isolatedHeap.rootScope();
    kyna::Value temporary(isolatedHeap.allocate());
    roots.protect(temporary);
    isolatedHeap.collect({});
    assert(isolatedHeap.live() == 1);
  }
  isolatedHeap.collect({});
  assert(isolatedHeap.live() == 0);

  {
    auto roots = isolatedHeap.rootScope();
    auto *closure = isolatedHeap.allocateClosure(1, {});
    auto *recursiveCell = isolatedHeap.allocateCaptureCell(kyna::Value(closure));
    closure->captures.push_back(recursiveCell);
    kyna::Value closureRoot(closure);
    roots.protect(closureRoot);
    isolatedHeap.collect({});
    assert(isolatedHeap.live() == 2);
  }
  isolatedHeap.collect({});
  assert(isolatedHeap.live() == 0);

  {
    auto roots = isolatedHeap.rootScope();
    auto *receiver = isolatedHeap.allocate();
    auto *method = isolatedHeap.allocateBoundMethod(receiver, 7);
    kyna::Value methodRoot(method);
    roots.protect(methodRoot);
    isolatedHeap.collect({});
    assert(isolatedHeap.live() == 2);
  }
  isolatedHeap.collect({});
  assert(isolatedHeap.live() == 0);

  {
    auto roots = isolatedHeap.rootScope();
    auto *cyclic = isolatedHeap.allocateArray();
    cyclic->elements.emplace_back(cyclic);
    kyna::Value cyclicRoot(cyclic);
    roots.protect(cyclicRoot);
    assert(cyclicRoot.display() == "[<cycle>]");
    isolatedHeap.collect({});
    assert(isolatedHeap.live() == 1);
  }
  isolatedHeap.collect({});
  assert(isolatedHeap.live() == 0);

  // A long alternating object/array cycle exercises the iterative tracer. A
  // recursive marker would risk overflowing the native stack here.
  {
    auto roots = isolatedHeap.rootScope();
    auto *first = isolatedHeap.allocate();
    kyna::Value graphRoot(first);
    roots.protect(graphRoot);
    auto *current = first;
    constexpr std::size_t depth = 4000;
    for (std::size_t index = 0; index < depth; ++index) {
      auto *array = isolatedHeap.allocateArray();
      current->fields["next"] = kyna::Value(array);
      auto *next = isolatedHeap.allocate();
      array->elements.emplace_back(next);
      current = next;
    }
    current->fields["next"] = graphRoot;
    isolatedHeap.collect({});
    const auto retained = isolatedHeap.stats();
    assert(retained.objects == depth + 1);
    assert(retained.arrays == depth);
    assert(retained.live == depth * 2 + 1);
  }
  isolatedHeap.collect({});
  const auto reclaimedGraph = isolatedHeap.stats();
  assert(reclaimedGraph.live == 0);
  assert(reclaimedGraph.reclaimed >= 8001);
  assert(reclaimedGraph.objects == 0 && reclaimedGraph.arrays == 0);
}
