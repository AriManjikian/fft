module twiddle_rom #(
    parameter int DATA_WIDTH = fft::DATA_WIDTH,
    parameter int DATA_DEPTH = fft::DATA_DEPTH,
    parameter string INIT_FILE = ""
) (
    input logic clk,
    input logic [$clog2(DATA_DEPTH)-1:0] i_addr,
    output logic [DATA_WIDTH-1:0] o_data
);

  logic [DATA_WIDTH-1:0] r_ram_array[DATA_DEPTH];

  initial begin
    integer i;

    for (i = 0; i < DATA_DEPTH; i++) begin
      r_ram_array[i] = '0;
    end

    if (INIT_FILE != "") begin
      $readmemh(INIT_FILE, r_ram_array);
    end
  end

  always_ff @(posedge clk) begin
    o_data <= r_ram_array[i_addr];
  end

endmodule
