module twiddle_rom_wrapper #(
    parameter int DATA_WIDTH = 16,
    parameter int DATA_DEPTH = 1024
) (
    input logic clk,
    input logic [$clog2(DATA_DEPTH)-1:0] i_addr,
    output logic [DATA_WIDTH-1:0] o_tr,
    output logic [DATA_WIDTH-1:0] o_ti
);

  string BASE_PATH;
  string real_file;
  string imag_file;

  logic [DATA_WIDTH-1:0] rom_re[0:DATA_DEPTH-1];
  logic [DATA_WIDTH-1:0] rom_im[0:DATA_DEPTH-1];

  integer i;

  initial begin
    $display("TWIDDLE ROM INIT START");

    if (!$value$plusargs("BASE_PATH=%s", BASE_PATH)) begin
      $fatal(1, "BASE_PATH not provided");
    end

    real_file = $sformatf("%s/fft_%0d/twiddles_real.txt", BASE_PATH, DATA_DEPTH);
    imag_file = $sformatf("%s/fft_%0d/twiddles_imag.txt", BASE_PATH, DATA_DEPTH);

    $display("real_file = %s", real_file);
    $display("imag_file = %s", imag_file);

    for (i = 0; i < DATA_DEPTH; i++) begin
      rom_re[i] = '0;
      rom_im[i] = '0;
    end

    $readmemh(real_file, rom_re);
    $readmemh(imag_file, rom_im);
  end

  always_ff @(posedge clk) begin
    o_tr <= rom_re[i_addr];
    o_ti <= rom_im[i_addr];
  end

endmodule
