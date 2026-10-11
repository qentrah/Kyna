kyna_add_module(kyna_typecheck SOURCES
  src/checkers/analyzer.cpp
  src/checkers/statement_checker.cpp
  src/checkers/check_declarations.cpp
  src/checkers/check_control_flow.cpp
  src/checkers/interface_checker.cpp
  src/checkers/type_checker.cpp
  src/checkers/type_contracts.cpp
  src/checkers/check_operators.cpp
  src/checkers/check_invocations.cpp
  src/checkers/check_conditionals.cpp
  src/checkers/best_practice_checker.cpp
  src/validators/modifier_rules.cpp
  src/catalog/interface_catalog.cpp
  src/validators/program_validation.cpp
  src/checkers/module_analyzer.cpp
  src/checkers/cycle_detector.cpp
  src/types/scope.cpp
  src/codecs/export_cache.cpp
  PUBLIC_DEPENDENCIES kyna_resolution kyna_symbols kyna_syntax kyna_types kyna_diagnostics)

# Invalidate checked contracts after compiler releases or checker implementation changes.
# Source inventories come from explicit target lists; no build sources are discovered.
set(kyna_contract_inputs
  include/kyna/semantics/modifier_query.hpp
  include/kyna/semantics/environment.hpp
  include/kyna/semantics/program_analyzer.hpp
  include/kyna/semantics/symbol.hpp
  include/kyna/semantics/module_analyzer.hpp
  include/kyna/semantics/checked_program.hpp
  include/kyna/semantics/program_validation.hpp
  include/kyna/semantics/interface_catalog.hpp
  include/kyna/semantics/cycle_detector.hpp
  include/kyna/semantics/scope.hpp
  include/kyna/semantics/export_cache.hpp
  src/checkers/best_practice_checker.hpp
  src/checkers/check_helpers.hpp
  ../kyna_syntax/include/kyna/syntax/ast_visitor.hpp
  ../kyna_syntax/include/kyna/syntax/syntax_tree.hpp
  ../kyna_syntax/include/kyna/syntax/declaration_nodes.hpp
  ../kyna_syntax/include/kyna/syntax/statement_nodes.hpp
  ../kyna_syntax/include/kyna/syntax/module_nodes.hpp
  ../kyna_syntax/include/kyna/syntax/legacy_syntax_handles.hpp
  ../kyna_syntax/include/kyna/syntax/expression_nodes.hpp
  ../kyna_types/include/kyna/semantics/type_model.hpp
  ../kyna_types/include/kyna/semantics/type_formatting.hpp)
list(TRANSFORM kyna_contract_inputs PREPEND "${CMAKE_CURRENT_SOURCE_DIR}/")
foreach(owner kyna_typecheck kyna_types kyna_symbols kyna_resolution kyna_parsing kyna_syntax kyna_lexing kyna_diagnostics)
  get_target_property(owner_sources ${owner} SOURCES)
  get_target_property(owner_directory ${owner} SOURCE_DIR)
  if(NOT owner_sources)
    continue()
  endif()
  foreach(source IN LISTS owner_sources)
    if(IS_ABSOLUTE "${source}")
      list(APPEND kyna_contract_inputs "${source}")
    else()
      list(APPEND kyna_contract_inputs "${owner_directory}/${source}")
    endif()
  endforeach()
endforeach()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${kyna_contract_inputs})
set(kyna_contract_hashes "${PROJECT_VERSION}")
foreach(source IN LISTS kyna_contract_inputs)
  file(SHA256 "${source}" source_hash)
  string(APPEND kyna_contract_hashes "${source_hash}")
endforeach()
string(SHA256 kyna_contract_build_id "${kyna_contract_hashes}")
target_compile_definitions(kyna_typecheck PRIVATE KYNA_EXPORT_CACHE_BUILD_ID="${PROJECT_VERSION}-${kyna_contract_build_id}")
