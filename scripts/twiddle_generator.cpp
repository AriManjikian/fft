#include <cmath>
#include <complex>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <vector>

namespace fs = std::filesystem;

const double PI = std::acos(-1);

bool is_power_of_two(int x) { return (x > 0) && ((x & (x - 1)) == 0); }

int16_t to_q15(double x) {
  if (x >= 1.0)
    return 0x7FFF;
  return static_cast<int16_t>(x * 32767.0);
}

std::vector<std::complex<double>> gen_tw_factors(int N,
                                                 const std::string &out_dir) {
  fs::create_directories(out_dir);

  std::ofstream real_file(fs::path(out_dir) / "twiddles_real.txt");
  std::ofstream imag_file(fs::path(out_dir) / "twiddles_imag.txt");

  std::vector<std::complex<double>> twiddles(N);

  for (int k = 0; k < N / 2; k++) {
    double angle = -2.0 * PI * k / N;

    twiddles[k] = {std::cos(angle), std::sin(angle)};

    uint16_t re_hex = to_q15(twiddles[k].real());
    uint16_t im_hex = to_q15(twiddles[k].imag());

    real_file << std::hex << std::uppercase << std::setw(4) << std::setfill('0')
              << re_hex << '\n';

    imag_file << std::hex << std::uppercase << std::setw(4) << std::setfill('0')
              << im_hex << '\n';
  }

  return twiddles;
}

int main() {
  int N;

  std::cout << "Enter N: ";
  std::cin >> N;

  fs::path source_dir = fs::path(__FILE__).parent_path();
  fs::path out_dir =
      source_dir / "twiddle_factors" / ("fft_" + std::to_string(N));

  if (!is_power_of_two(N)) {
    std::cout << "N must be a power of 2\n";
    return 1;
  }

  gen_tw_factors(N, out_dir);

  return 0;
}
