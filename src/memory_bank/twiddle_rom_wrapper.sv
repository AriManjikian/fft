module twiddle_rom_wrapper #(
    parameter int DATA_WIDTH = 16,
    parameter int DATA_DEPTH = 32,
    parameter string PRELOAD_DIRECTIVE = "build"
) (
    input logic clk,
    input logic [$clog2(DATA_DEPTH)-1:0] i_addr,
    output logic [DATA_WIDTH-1:0] o_tr,
    output logic [DATA_WIDTH-1:0] o_ti
);

  localparam string C_INIT_FILE_RE_SRC = "../../scripts/twiddle_factors/fft_%0d/twiddles_real.txt";
  localparam string C_INIT_FILE_IM_SRC = "../../scripts/twiddle_factors/fft_%0d/twiddles_imag.txt";
  localparam string C_INIT_FILE_RE_TB =
        "../../../scripts/twiddle_factors/fft_%0d/twiddles_real.txt";
  localparam string C_INIT_FILE_IM_TB =
        "../../../scripts/twiddle_factors/fft_%0d/twiddles_imag.txt";

  string real_file;
  string imag_file;

  initial begin
    if (PRELOAD_DIRECTIVE == "build") begin
      real_file = $sformatf(C_INIT_FILE_RE_SRC, DATA_DEPTH);
      imag_file = $sformatf(C_INIT_FILE_IM_SRC, DATA_DEPTH);
    end else if (PRELOAD_DIRECTIVE == "testbench") begin
      real_file = $sformatf(C_INIT_FILE_RE_TB, DATA_DEPTH);
      imag_file = $sformatf(C_INIT_FILE_IM_TB, DATA_DEPTH);
    end else begin
      $fatal(1, "Expected PRELOAD_DIRECTIVE = build or testbench, got %s", PRELOAD_DIRECTIVE);
    end
  end

  logic [DATA_WIDTH-1:0] rom_re[0:DATA_DEPTH-1];
  logic [DATA_WIDTH-1:0] rom_im[0:DATA_DEPTH-1];

  initial begin
    integer i;

    for (i = 0; i < DATA_DEPTH; i++) begin
      rom_re[i] = '0;
      rom_im[i] = '0;
    end

    if (PRELOAD_DIRECTIVE == "build") begin
      $readmemh($sformatf(C_INIT_FILE_RE_SRC, DATA_DEPTH), rom_re);
      $readmemh($sformatf(C_INIT_FILE_IM_SRC, DATA_DEPTH), rom_im);
    end else if (PRELOAD_DIRECTIVE == "testbench") begin
      $readmemh($sformatf(C_INIT_FILE_RE_TB, DATA_DEPTH), rom_re);
      $readmemh($sformatf(C_INIT_FILE_IM_TB, DATA_DEPTH), rom_im);
    end
  end

  always_ff @(posedge clk) begin
    o_tr <= rom_re[i_addr];
    o_ti <= rom_im[i_addr];
  end

endmodule
