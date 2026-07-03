module complex_mult #(
    parameter int DATA_WIDTH_A = fft::DATA_WIDTH,
    parameter int DATA_WIDTH_B = fft::DATA_WIDTH
) (
    input logic clk,
    // Input A
    input logic signed [DATA_WIDTH_A-1:0] i_ar,
    input logic signed [DATA_WIDTH_A-1:0] i_ai,
    // Input B
    input logic signed [DATA_WIDTH_B-1:0] i_br,
    input logic signed [DATA_WIDTH_B-1:0] i_bi,
    // Output P
    output logic signed [DATA_WIDTH_A+DATA_WIDTH_B:0] o_pr,
    output logic signed [DATA_WIDTH_A+DATA_WIDTH_B:0] o_pi
);

  logic signed [DATA_WIDTH_A-1:0] r_ar;
  logic signed [DATA_WIDTH_A-1:0] r_ar_d1;
  logic signed [DATA_WIDTH_A-1:0] r_ar_d2;

  logic signed [DATA_WIDTH_A-1:0] r_ai;
  logic signed [DATA_WIDTH_A-1:0] r_ai_d1;
  logic signed [DATA_WIDTH_A-1:0] r_ai_d2;

  logic signed [DATA_WIDTH_B-1:0] r_br;
  logic signed [DATA_WIDTH_B-1:0] r_br_d1;
  logic signed [DATA_WIDTH_B-1:0] r_br_d2;

  logic signed [DATA_WIDTH_B-1:0] r_bi;
  logic signed [DATA_WIDTH_B-1:0] r_bi_d1;
  logic signed [DATA_WIDTH_B-1:0] r_bi_d2;

  logic signed [DATA_WIDTH_A:0] r_add_common;
  logic signed [DATA_WIDTH_A+DATA_WIDTH_B:0] r_mult_common;
  logic signed [DATA_WIDTH_A+DATA_WIDTH_B:0] r_common;

  logic signed [DATA_WIDTH_B:0] r_add_re;
  logic signed [DATA_WIDTH_B:0] r_add_im;

  logic signed [DATA_WIDTH_A+DATA_WIDTH_B:0] r_mult_re;
  logic signed [DATA_WIDTH_A+DATA_WIDTH_B:0] r_mult_im;

  logic signed [DATA_WIDTH_A+DATA_WIDTH_B:0] r_pr;
  logic signed [DATA_WIDTH_A+DATA_WIDTH_B:0] r_pi;

  always_ff @(posedge clk) begin

    r_ar <= i_ar;
    r_ai <= i_ai;
    r_br <= i_br;
    r_bi <= i_bi;

    r_ar_d1 <= r_ar;
    r_ai_d1 <= r_ai;
    r_br_d1 <= r_br;
    r_bi_d1 <= r_bi;

    r_ar_d2 <= r_ar_d1;
    r_ai_d2 <= r_ai_d1;
    r_br_d2 <= r_br_d1;
    r_bi_d2 <= r_bi_d1;
  end

  // C = (Ar - Ai) * Bi
  always_ff @(posedge clk) begin
    r_add_common <= $signed(r_ar) - $signed(r_ai);
    r_mult_common <= r_add_common * r_bi_d1;
    r_common <= r_mult_common;
  end


  // P_r = (Br - Bi) * Ar + (Ar - Ai) * Bi = Ar*Br - Ai*Bi = (Br - Bi) * Ar + C
  always_ff @(posedge clk) begin
    r_add_re <= $signed(r_br_d1) - $signed(r_bi_d1);
    r_mult_re <= r_ar_d2 * r_add_re;
    r_pr <= r_mult_re + r_common;
  end

  // P_i = (Br + Bi) * Ai + (Ar - Ai) * Bi = Ai*Br + Ar*Bi = (Br + Bi) * Ai + C
  always_ff @(posedge clk) begin
    r_add_im <= $signed(r_bi_d1) + $signed(r_br_d1);
    r_mult_im <= r_ai_d2 * r_add_im;
    r_pi <= r_mult_im + r_common;
  end

  assign o_pr = r_pr;
  assign o_pi = r_pi;
endmodule
