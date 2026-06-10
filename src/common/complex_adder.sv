module complex_adder #(
    parameter int DATA_WIDTH
) (
    input logic clk,
    input logic signed [DATA_WIDTH-1:0] i_ar,
    input logic signed [DATA_WIDTH-1:0] i_ai,
    input logic signed [DATA_WIDTH-1:0] i_br,
    input logic signed [DATA_WIDTH-1:0] i_bi,
    output logic signed [DATA_WIDTH:0] o_cr,
    output logic signed [DATA_WIDTH:0] o_ci
);

  logic signed [DATA_WIDTH:0] r_cr_signed;
  logic signed [DATA_WIDTH:0] r_ci_signed;


  always_ff @(posedge clk) begin

    r_cr_signed <= $signed({i_ar[DATA_WIDTH-1], i_ar}) + $signed({i_br[DATA_WIDTH-1], i_br});

    r_ci_signed <= $signed({i_ai[DATA_WIDTH-1], i_ai}) + $signed({i_bi[DATA_WIDTH-1], i_bi});
  end

  assign o_cr = r_cr_signed;
  assign o_ci = r_ci_signed;
endmodule
