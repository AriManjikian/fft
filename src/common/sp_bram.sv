module sp_bram #(
    parameter int RAM_WIDTH = 16,
    parameter int RAM_DEPTH_BITS = 10
) (
    input logic clk,
    input logic [RAM_DEPTH_BITS-1:0] i_addr,
    input logic [RAM_WIDTH-1:0] i_din,
    input logic i_we,
    output logic [RAM_WIDTH-1:0] o_dout
);

  localparam int C_RAM_WIDTH = RAM_WIDTH;
  localparam int C_RAM_DEPTH = 2 ** RAM_DEPTH_BITS;

  logic [C_RAM_WIDTH-1:0] ram[C_RAM_DEPTH];

  always_ff @(posedge clk) begin
    if (i_we) begin
      ram[i_addr] <= i_din;
    end
    o_dout <= ram[i_addr];
  end
endmodule
