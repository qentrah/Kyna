#pragma once
#include <kyna/language/native_functions.hpp>
namespace kyna::native {
NativeCallFailure thrownFailure(const RuntimeThrownError &);
}
