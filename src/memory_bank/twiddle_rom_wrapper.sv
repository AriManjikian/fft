module twiddle_rom_wrapper #(
    parameter int DATA_WIDTH = fft::DATA_WIDTH,
    parameter int DATA_DEPTH = fft::DATA_DEPTH
) (
    input logic i_Clk,
    input logic [$clog2(DATA_DEPTH)-1:0] i_addr,
    output logic [DATA_WIDTH-1:0] o_tr,
    output logic [DATA_WIDTH-1:0] o_ti
);

  logic [DATA_WIDTH-1:0] rom_re[0:DATA_DEPTH-1];
  logic [DATA_WIDTH-1:0] rom_im[0:DATA_DEPTH-1];

  always_ff @(posedge i_Clk) begin
    o_tr <= rom_re[i_addr];
    o_ti <= rom_im[i_addr];
  end

`ifndef SYNTHESIS

  // ---------------- Simulation ----------------

  string BASE_PATH;
  string real_file;
  string imag_file;

  initial begin
    $display("TWIDDLE ROM INIT START");

    if (!$value$plusargs("BASE_PATH=%s", BASE_PATH)) begin
      $fatal(1, "BASE_PATH not provided");
    end

    real_file = $sformatf("%s/fft_%0d/twiddles_real.txt", BASE_PATH, DATA_DEPTH);

    imag_file = $sformatf("%s/fft_%0d/twiddles_imag.txt", BASE_PATH, DATA_DEPTH);

    $display("real_file = %s", real_file);
    $display("imag_file = %s", imag_file);

    $readmemh(real_file, rom_re);
    $readmemh(imag_file, rom_im);
  end

`else

  // ---------------- Synthesis ----------------

  initial begin
    $readmemh("twiddles_real.mem", rom_re);
    $readmemh("twiddles_imag.mem", rom_im);
  end

`endif

endmodule
