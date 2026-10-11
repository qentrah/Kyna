#pragma once
#include <optional>
namespace kyna {
struct Value;
// Exact integer/mixed comparisons; nullopt represents unordered NaN/non-numbers.
std::optional<int> compareNumbers(const Value &, const Value &);
}
