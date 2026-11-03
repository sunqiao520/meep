// A small simulation for setting breakpoints and inspecting Meep state in VS.
#include <meep.hpp>
#include <cmath>
#include <iostream>

double vacuum_epsilon(const meep::vec &) { return 1.0; }

int main(int argc, char **argv) {
  meep::initialize runtime(argc, argv);
  auto grid = meep::vol2d(4.0, 4.0, 10.0);
  grid.center_origin();
  meep::structure geometry(grid, vacuum_epsilon, meep::pml(0.5));
  meep::fields fields(&geometry);
  meep::gaussian_src_time source(1.0, 0.5);
  fields.add_point_source(meep::Ez, source, meep::vec(0.0, 0.0));

  while (fields.time() < 10.0) {
    fields.step(); // Set a breakpoint here; F11 enters src/step.cpp.
  }
  const auto value = fields.get_field(meep::Ez, meep::vec(0.2, 0.0));
  std::cout << "time=" << fields.time() << " Ez=" << value << '\n';
  return std::isfinite(value.real()) && std::isfinite(value.imag()) ? 0 : 1;
}
