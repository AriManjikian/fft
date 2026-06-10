module butterfly #(
    parameter int DATA_WIDTH  = 16,
    parameter int DATA_FORMAT = 15
) (
    input logic clk,
    // Input A
    input logic signed [DATA_WIDTH-1:0] i_ar,
    input logic signed [DATA_WIDTH-1:0] i_ai,
    // Input B
    input logic signed [DATA_WIDTH-1:0] i_br,
    input logic signed [DATA_WIDTH-1:0] i_bi,
    // Input Twiddle
    input logic signed [DATA_WIDTH-1:0] i_tr,
    input logic signed [DATA_WIDTH-1:0] i_ti,
    // Output X
    output logic signed [DATA_WIDTH-1:0] o_xr,
    output logic signed [DATA_WIDTH-1:0] o_xi,
    // Output Y
    output logic signed [DATA_WIDTH-1:0] o_yr,
    output logic signed [DATA_WIDTH-1:0] o_yi
);

  parameter int NUM_PIPELINE_STAGES = 6;

  logic signed [DATA_WIDTH:0] r_pipe_data_re[NUM_PIPELINE_STAGES];
  logic signed [DATA_WIDTH:0] r_pipe_data_im[NUM_PIPELINE_STAGES];

  logic signed [2*DATA_WIDTH:0] w_cmult_out_re;
  logic signed [2*DATA_WIDTH:0] w_cmult_out_im;

  logic signed [DATA_WIDTH:0] w_cmult_out_re_trunc;
  logic signed [DATA_WIDTH:0] w_cmult_out_im_trunc;

  logic signed [DATA_WIDTH:0] r_cmult_out_re_trunc;
  logic signed [DATA_WIDTH:0] r_cmult_out_im_trunc;

  logic signed [DATA_WIDTH+1:0] w_xr;
  logic signed [DATA_WIDTH+1:0] w_xi;
  logic signed [DATA_WIDTH+1:0] w_yr;
  logic signed [DATA_WIDTH+1:0] w_yi;

  logic r_overflow_mult;
  logic r_overflow_out;

  // Pipeline
  integer i;
  always_ff @(posedge clk) begin
    for (i = NUM_PIPELINE_STAGES - 1; i > 0; i--) begin
      r_pipe_data_re[i] <= r_pipe_data_re[i-1];
      r_pipe_data_im[i] <= r_pipe_data_im[i-1];
    end

    // sign extend by 1 bit
    r_pipe_data_re[0] <= $signed({i_ar[DATA_WIDTH-1], i_ar});
    r_pipe_data_im[0] <= $signed({i_ai[DATA_WIDTH-1], i_ai});
  end

  complex_mult #(
      .DATA_WIDTH_A(DATA_WIDTH  /* default 16 */),
      .DATA_WIDTH_B(DATA_WIDTH  /* default 16 */)
  ) complex_mult (
      .clk (clk),
      .i_ar(i_br),
      .i_ai(i_bi),
      .i_br(i_tr),
      .i_bi(i_ti),
      .o_pr(w_cmult_out_re),
      .o_pi(w_cmult_out_im)
  );

  always_ff @(posedge clk) begin
    r_overflow_mult <= 1'b0;

    // Real
    if (w_cmult_out_re[$high(w_cmult_out_re)] != w_cmult_out_re[$high(w_cmult_out_re)-1]) begin

      r_cmult_out_re_trunc <= {
        w_cmult_out_re[$high(w_cmult_out_re)], {DATA_WIDTH{w_cmult_out_re[$high(w_cmult_out_re)-1]}}
      };

      r_overflow_mult <= 1'b1;
    end else begin
      r_cmult_out_re_trunc <= $signed(w_cmult_out_re[$high(w_cmult_out_re)-1-:(DATA_WIDTH+1)]);
    end

    // Imag
    if (w_cmult_out_im[$high(w_cmult_out_im)] != w_cmult_out_im[$high(w_cmult_out_im)-1]) begin

      r_cmult_out_im_trunc <= {
        w_cmult_out_im[$high(w_cmult_out_im)], {DATA_WIDTH{w_cmult_out_im[$high(w_cmult_out_im)-1]}}
      };

      r_overflow_mult <= 1'b1;
    end else begin
      r_cmult_out_im_trunc <= $signed(w_cmult_out_im[$high(w_cmult_out_im)-1-:(DATA_WIDTH+1)]);
    end
  end

  // X = A + T*B
  complex_adder #(
      .DATA_WIDTH(DATA_WIDTH + 1)
  ) complex_adder_A (
      .clk (clk),
      .i_ar(r_pipe_data_re[$high(r_pipe_data_re)]),
      .i_ai(r_pipe_data_im[$high(r_pipe_data_im)]),
      .i_br(r_cmult_out_re_trunc),
      .i_bi(r_cmult_out_im_trunc),
      .o_cr(w_xr),
      .o_ci(w_xi)
  );
  // Y = A - T*B
  complex_adder #(
      .DATA_WIDTH(DATA_WIDTH + 1)
  ) complex_adder_B (
      .clk (clk),
      .i_ar(r_pipe_data_re[$high(r_pipe_data_re)]),
      .i_ai(r_pipe_data_im[$high(r_pipe_data_im)]),
      .i_br(-r_cmult_out_re_trunc),
      .i_bi(-r_cmult_out_im_trunc),
      .o_cr(w_yr),
      .o_ci(w_yi)
  );

  always_ff @(posedge clk) begin
    r_overflow_out <= 1'b0;

    // XR
    if (w_xr[DATA_WIDTH+1] != w_xr[DATA_WIDTH]) begin
      o_xr <= {w_xr[DATA_WIDTH+1], {DATA_WIDTH - 1{w_xr[DATA_WIDTH]}}};
      r_overflow_out <= 1'b1;
    end else begin
      o_xr <= w_xr[DATA_WIDTH:1];
    end

    // XI
    if (w_xi[DATA_WIDTH+1] != w_xi[DATA_WIDTH]) begin
      o_xi <= {w_xi[DATA_WIDTH+1], {DATA_WIDTH - 1{w_xi[DATA_WIDTH]}}};
      r_overflow_out <= 1'b1;
    end else begin
      o_xi <= w_xi[DATA_WIDTH:1];
    end

    // YR
    if (w_yr[DATA_WIDTH+1] != w_yr[DATA_WIDTH]) begin
      o_yr <= {w_yr[DATA_WIDTH+1], {DATA_WIDTH - 1{w_yr[DATA_WIDTH]}}};
      r_overflow_out <= 1'b1;
    end else begin
      o_yr <= w_yr[DATA_WIDTH:1];
    end

    // YI
    if (w_yi[DATA_WIDTH+1] != w_yi[DATA_WIDTH]) begin
      o_yi <= {w_yi[DATA_WIDTH+1], {DATA_WIDTH - 1{w_yi[DATA_WIDTH]}}};
      r_overflow_out <= 1'b1;
    end else begin
      o_yi <= w_yi[DATA_WIDTH:1];
    end
  end
endmodule
