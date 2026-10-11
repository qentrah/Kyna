// Owns GUI embedding contracts: lazy startup, host application type and UI thread.
#include <kyna/language/language_session.hpp>
#include <kyna/language/native_modules.hpp>
#include <QCoreApplication>
#include <QGuiApplication>
#include <cassert>
#include <iostream>
#include <thread>

namespace {
void exercise(const char *library, const std::string &code) {
  kyna::LanguageSessionOptions options;
  options.nativeFunctions=kyna::loadNativeModule(library);
  kyna::LanguageSession session(std::move(options));
  auto result=session.runSource("gui-host.ky", "fn stop(): void { guiQuit(); } var timer=guiAfter(1,stop); collectGarbage(); guiRun();");
  if(code.empty()) {
    for(const auto &diagnostic:result.diagnostics)std::cerr<<diagnostic.code<<": "<<diagnostic.message<<'\n';
    assert(result.ok());
  } else {
    assert(!result.ok());
    assert(!result.diagnostics.empty());
    assert(result.diagnostics.front().code==code);
  }
}
}
int main(int argc,char **argv) {
  assert(argc==3);const std::string mode=argv[2];
  // Loading/checking exports must not create a Qt application.
  {
    kyna::LanguageSessionOptions options;options.nativeFunctions=kyna::loadNativeModule(argv[1]);
    kyna::LanguageSession session(std::move(options));
    assert(session.checkSource("gui-check.ky","fn later(): void { guiQuit(); } var id=guiAfter(1,later);").ok());
    assert(QCoreApplication::instance()==nullptr);
  }
  if(mode=="core") { QCoreApplication app(argc,argv);exercise(argv[1],"KNATIVE1005"); }
  else {
    QGuiApplication app(argc,argv);
    if(mode=="gui") { exercise(argv[1],"");exercise(argv[1],""); }
    else {
      assert(mode=="thread");
      std::thread worker([&]{exercise(argv[1],"KNATIVE1007");});worker.join();
    }
  }
  std::cout<<"GUI embedding contract passed: "<<mode<<'\n';
}
