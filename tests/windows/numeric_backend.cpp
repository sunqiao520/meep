// Exercise the numerical ABI and the interleaved batch layout used by MPB.
#include <mkl.h>
#include <fftw3.h>
#include <algorithm>
#include <cmath>
#include <complex>
#include <iostream>
#include <vector>

int main() {
  static_assert(sizeof(MKL_INT) == 4, "Meep's current numerical interface requires LP64");
  const double matrix[4] = {4, 1, 2, 3};
  double inverse[4];
  std::copy(matrix, matrix + 4, inverse);
  MKL_INT pivots[2];
  if (LAPACKE_dgetrf(LAPACK_COL_MAJOR, 2, 2, inverse, 2, pivots) ||
      LAPACKE_dgetri(LAPACK_COL_MAJOR, 2, inverse, 2, pivots)) return 1;
  double product[4];
  cblas_dgemm(CblasColMajor, CblasNoTrans, CblasNoTrans, 2, 2, 2,
              1, matrix, 2, inverse, 2, 0, product, 2);
  for (int i = 0; i < 4; ++i)
    if (std::abs(product[i] - (i % 3 == 0 ? 1.0 : 0.0)) > 1e-12) return 2;
  const std::complex<double> x[] = {{1, 2}, {3, -4}};
  const std::complex<double> y[] = {{2, -1}, {-1, 3}};
  std::complex<double> dot;
  cblas_zdotc_sub(2, x, 1, y, 1, &dot);
  if (std::abs(dot - std::complex<double>(-15, 0)) > 1e-12) return 3;

  int dimensions[] = {2, 3, 5};
  constexpr int points = 30, batches = 3;
  auto *data = static_cast<fftw_complex *>(fftw_malloc(sizeof(fftw_complex) * points * batches));
  if (!data) return 4;
  std::vector<std::complex<double>> reference(points * batches);
  for (int i = 0; i < points * batches; ++i) {
    reference[i] = {std::sin(0.7 * i), std::cos(0.3 * i)};
    data[i][0] = reference[i].real();
    data[i][1] = reference[i].imag();
  }
  auto forward = fftw_plan_many_dft(3, dimensions, batches, data, nullptr, batches, 1,
                                    data, nullptr, batches, 1, FFTW_FORWARD, FFTW_ESTIMATE);
  auto backward = fftw_plan_many_dft(3, dimensions, batches, data, nullptr, batches, 1,
                                     data, nullptr, batches, 1, FFTW_BACKWARD, FFTW_ESTIMATE);
  if (!forward || !backward) return 5;
  fftw_execute(forward);
  fftw_execute(backward);
  double error = 0;
  for (int i = 0; i < points * batches; ++i)
    error = std::max(error, std::abs(std::complex<double>(data[i][0], data[i][1]) / double(points) - reference[i]));
  fftw_destroy_plan(forward);
  fftw_destroy_plan(backward);
  fftw_free(data);
  std::cout << "oneMKL LP64 BLAS/LAPACK and FFTW3 interleaved batch error: " << error << '\n';
  return error > 1e-12 ? 6 : 0;
}
