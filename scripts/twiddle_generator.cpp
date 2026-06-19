#include <cmath>
#include <complex>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <vector>

const double PI = std::acos(-1);

bool is_power_of_two(int x) { return (x > 0) && ((x & (x - 1)) == 0); }

int16_t to_q15(double x) {
  if (x >= 1.0)
    return 0x7FFF;
  return static_cast<int16_t>(x * 32767.0);
}

std::vector<std::complex<double>> gen_tw_factors(int N) {
  std::vector<std::complex<double>> twiddles(N);

  std::ofstream outfile("twiddles.txt");

  outfile << "k,real,imag,real_hex,imag_hex\n";

  for (int k = 0; k < N; k++) {
    double angle = -2.0 * PI * k / N;

    twiddles[k] = {std::cos(angle), -std::sin(angle)};

    uint16_t re_hex = to_q15(twiddles[k].real());
    uint16_t im_hex = to_q15(twiddles[k].imag());

    std::cout << "k=" << std::setw(2) << k << "  Re=" << std::setw(12)
              << twiddles[k].real() << "  Im=" << std::setw(12)
              << twiddles[k].imag() << "  ReHex=0x" << std::hex << std::setw(16)
              << std::setfill('0') << re_hex << "  ImHex=0x" << std::setw(16)
              << im_hex << std::dec << std::setfill(' ') << '\n';

    outfile << k << "," << twiddles[k].real() << "," << twiddles[k].imag()
            << "," << "0x" << std::hex << re_hex << "," << "0x" << im_hex
            << std::dec << "\n";
  }

  return twiddles;
}

int main() {
  int N;

  std::cout << "Enter N: ";
  std::cin >> N;

  if (!is_power_of_two(N)) {
    std::cout << "N must be a power of 2\n";
    return 1;
  }

  gen_tw_factors(N);

  return 0;
}
