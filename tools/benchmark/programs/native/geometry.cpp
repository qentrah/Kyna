// Owns the fixed convex-hull C++ performance oracle.
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/convex_hull_2.h>
#include <iostream>
#include <vector>
int main() {
  using K = CGAL::Exact_predicates_inexact_constructions_kernel;
  std::vector<K::Point_2> points{{0,0},{100,0},{100,100},{0,100},{50,50}};
  std::size_t count = 0;
  for (int iteration = 0; iteration < 1000; ++iteration) {
    std::vector<K::Point_2> hull;
    CGAL::convex_hull_2(points.begin(), points.end(), std::back_inserter(hull));
    count += hull.size();
    if (hull.size() != 4 || hull[0] != K::Point_2(0,0) ||
        hull[1] != K::Point_2(100,0) || hull[2] != K::Point_2(100,100) ||
        hull[3] != K::Point_2(0,100)) return 1;
  }
  std::cout << count << '\n';
}
