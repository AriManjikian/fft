import fft::*;
module fft_top #(

    parameter int NFFT = 32,
    parameter int DATA_WIDTH = 16,
    parameter int QFORMAT = 15
) (
    input logic clk,
    input logic reset,
    input logic [DATA_WIDTH-1:0] i_tdata_re,
    input logic [DATA_WIDTH-1:0] i_tdata_im,
    input logic i_tvalid,
    output logic o_tready,

    output logic [DATA_WIDTH-1:0] o_tdata_re,
    output logic [DATA_WIDTH-1:0] o_tdata_im,
    output logic [$clog2(NFFT)-1:0] o_xk_index,
    output logic o_tvalid
);

  localparam int C_NFFT_LOG2 = $clog2(NFFT);

  // Memory Write Address Pipeline
  typedef logic [C_NFFT_LOG2-1:0] t_mem_waddr_pipe[0:C_BFU_LATENCY-1];
  t_mem_waddr_pipe r_wr_addr_mem_a_pipe = '{default: '0};
  t_mem_waddr_pipe r_wr_addr_mem_b_pipe = '{default: '0};

  // Memory Write Enable Pipeline
  typedef logic [C_MEM_SEL_PIPE-1:0] t_mem_wren_pipe;
  t_mem_wren_pipe r_wr_en_mem_pipe = '0;

  // FFT State Machine
  typedef enum logic [2:0] {
    IDLE,
    FILL_BUFFER,
    LOAD_UNLOAD,
    RUN,
    HOLD
  } fft_state_t;
  fft_state_t                     s_fft_state = IDLE;

  // AGU
  logic                           w_agu_start;
  logic                           w_agu_done;

  logic                           w_agu_wr_en;
  logic        [ C_NFFT_LOG2-1:0] w_agu_rd_addr_a;
  logic        [ C_NFFT_LOG2-1:0] w_agu_rd_addr_b;
  logic        [ C_NFFT_LOG2-2:0] w_agu_rd_addr_tw;
  logic                           r_agu_wr_en = 1'b0;
  logic        [ C_NFFT_LOG2-1:0] r_rd_addr_mem_a = '0;
  logic        [ C_NFFT_LOG2-1:0] r_rd_addr_mem_b = '0;
  logic        [ C_NFFT_LOG2-1:0] r_rd_addr_twiddle = '0;
  logic        [ C_NFFT_LOG2-1:0] r_rd_addr_twiddle_d1 = '0;
  logic        [ C_NFFT_LOG2-1:0] r_rd_addr_twiddle_d2 = '0;

  // Memory Banks
  logic                           r_mem_select = 1'b0;
  logic                           w_wr_en_1;
  logic                           w_wr_en_2;
  logic signed [  DATA_WIDTH-1:0] w_stored_xr;
  logic signed [  DATA_WIDTH-1:0] w_stored_xi;
  logic signed [  DATA_WIDTH-1:0] w_stored_yr;
  logic signed [  DATA_WIDTH-1:0] w_stored_yi;
  logic signed [  DATA_WIDTH-1:0] w_calculated_xr;
  logic signed [  DATA_WIDTH-1:0] w_calculated_xi;
  logic signed [  DATA_WIDTH-1:0] w_calculated_yr;
  logic signed [  DATA_WIDTH-1:0] w_calculated_yi;

  // Bit Reverse
  logic        [  DATA_WIDTH-1:0] w_br_to_mb_tdata_re;
  logic        [  DATA_WIDTH-1:0] w_br_to_mb_tdata_im;
  logic        [ C_NFFT_LOG2-1:0] w_br_to_mb_addr_reversed;
  logic        [ C_NFFT_LOG2-1:0] w_br_to_mb_addr_normal;
  logic                           w_br_tvalid_out;

  // Twiddle ROM
  logic signed [  DATA_WIDTH-1:0] w_twiddle_tr;
  logic signed [  DATA_WIDTH-1:0] w_twiddle_ti;

  // Buffers
  logic                           w_buffer_tvalid_in;
  logic        [ C_NFFT_LOG2-1:0] r_input_buf_addr;
  logic        [2*DATA_WIDTH-1:0] w_buffer_re_im_in;
  logic        [2*DATA_WIDTH-1:0] w_buffer_re_im_out;
  logic        [  DATA_WIDTH-1:0] w_buffer_re_out;
  logic        [  DATA_WIDTH-1:0] w_buffer_im_out;
  logic                           r_buffer_tvalid_out = 1'b0;

  // Auxiliary Signals
  logic                           w_agu_wr_rising_edge;
  logic                           w_wr_en_mem_ab;
  logic        [ C_NFFT_LOG2-1:0] w_wr_addr_mem_a;
  logic        [ C_NFFT_LOG2-1:0] w_wr_addr_mem_b;
  logic        [             4:0] r_hold_counter = '0;
  logic                           w_tready_out;
  logic        [             2:0] r_tvalid_out_pipeline = '0;

  assign w_buffer_tvalid_in = i_tvalid && (s_fft_state == FILL_BUFFER);
  assign w_agu_start = w_br_tvalid_out && (int'(w_br_to_mb_addr_normal) == (NFFT - 1));
  assign w_tready_out = (s_fft_state == FILL_BUFFER);
  assign o_tready = w_tready_out;
  assign o_tvalid = r_tvalid_out_pipeline[2];

  // FSM
  always_ff @(posedge clk) begin
    if (reset) begin
      s_fft_state <= IDLE;
    end else begin
      case (s_fft_state)
        IDLE: begin
          s_fft_state <= FILL_BUFFER;
        end
        FILL_BUFFER: begin
          if (i_tvalid) begin
            if (int'(r_input_buf_addr) >= NFFT - 1) begin
              s_fft_state <= LOAD_UNLOAD;
            end
          end
        end
        LOAD_UNLOAD: begin
          if (int'(r_input_buf_addr) >= NFFT - 1) begin
            s_fft_state <= RUN;
          end
        end
        RUN: begin
          if (w_agu_done) begin
            s_fft_state <= HOLD;
          end
        end
        HOLD: begin
          if (r_hold_counter[4]) begin
            s_fft_state <= FILL_BUFFER;
          end
        end
        default: s_fft_state <= IDLE;
      endcase
    end
  end

  // FFT Control
  always_ff @(posedge clk) begin
    r_buffer_tvalid_out <= '0;
    r_hold_counter <= '0;
    if (s_fft_state == IDLE) begin
      r_input_buf_addr <= '0;
      r_hold_counter <= '0;
      r_mem_select <= '0;
    end else if (s_fft_state == FILL_BUFFER) begin
      if (w_buffer_tvalid_in) begin
        if (int'(r_input_buf_addr) >= (NFFT - 1)) r_input_buf_addr <= '0;
        else r_input_buf_addr <= r_input_buf_addr + 1'b1;
      end
    end else if (s_fft_state == LOAD_UNLOAD) begin
      r_buffer_tvalid_out <= 1'b1;
      if (int'(r_input_buf_addr) >= (NFFT - 1)) r_input_buf_addr <= '0;
      else r_input_buf_addr <= r_input_buf_addr + 1'b1;
    end else if (s_fft_state == RUN) begin
      if (w_agu_wr_rising_edge) begin
        r_mem_select <= ~r_mem_select;
      end
    end else if (s_fft_state == HOLD) begin
      r_hold_counter <= r_hold_counter + 1'b1;
      if (r_hold_counter[$high(r_hold_counter)]) begin
        r_hold_counter <= '0;
        r_mem_select   <= ~r_mem_select;
      end
    end
  end

  // Edge detector
  always_ff @(posedge clk) begin
    r_agu_wr_en <= w_agu_wr_en;
  end
  assign w_agu_wr_rising_edge = ~(r_agu_wr_en) && w_agu_wr_en;

  // Pipeline
  always_ff @(posedge clk) begin
    r_wr_addr_mem_a_pipe[0] <= w_agu_rd_addr_a;
    r_wr_addr_mem_b_pipe[0] <= w_agu_rd_addr_b;
    for (int i = 1; i < C_BFU_LATENCY; i++) begin
      r_wr_addr_mem_a_pipe[i] <= r_wr_addr_mem_a_pipe[i-1];
      r_wr_addr_mem_b_pipe[i] <= r_wr_addr_mem_b_pipe[i-1];
    end
    r_wr_en_mem_pipe <= {
        r_wr_en_mem_pipe[C_MEM_SEL_PIPE-2:0],
        w_agu_wr_en
    };
    r_rd_addr_mem_a <= w_agu_rd_addr_a;
    r_rd_addr_mem_b <= w_agu_rd_addr_b;
    r_rd_addr_twiddle    <= {1'b0, w_agu_rd_addr_tw};
    r_rd_addr_twiddle_d1 <= r_rd_addr_twiddle;
    r_rd_addr_twiddle_d2 <= r_rd_addr_twiddle_d1;
    r_tvalid_out_pipeline <= {
        r_tvalid_out_pipeline[1:0],
        w_br_tvalid_out
    };
  end
  assign w_wr_en_mem_ab  = r_wr_en_mem_pipe[$high(r_wr_en_mem_pipe)];
  assign w_wr_addr_mem_a = r_wr_addr_mem_a_pipe[$high(r_wr_addr_mem_a_pipe)];
  assign w_wr_addr_mem_b = r_wr_addr_mem_b_pipe[$high(r_wr_addr_mem_b_pipe)];

  // AGU
  agu #(
      .DATA_DEPTH_LOG2(C_NFFT_LOG2  /* default 5 */)
  ) agu_inst (
      .clk            (clk),
      .i_start        (w_agu_start),
      .o_done         (w_agu_done),
      .o_wr_en        (w_agu_wr_en),
      .o_raddr_mem_a  (w_agu_rd_addr_a),
      .o_raddr_mem_b  (w_agu_rd_addr_b),
      .o_raddr_twiddle(w_agu_rd_addr_tw)
  );

  // Memory Bank
  assign w_wr_en_1 = w_wr_en_mem_ab && (~r_mem_select);
  assign w_wr_en_2 = w_wr_en_mem_ab && r_mem_select;

  memory_bank_wrapper #(
      .DATA_WIDTH     (DATA_WIDTH  /* default 16 */),
      .DATA_DEPTH_LOG2(C_NFFT_LOG2  /* default 5 */)
  ) memory_bank_wrapper_inst (
      .clk               (clk),
      .i_bank_select     (r_mem_select),
      .i_load_unload     (w_br_tvalid_out),
      .i_addr_load       (w_br_to_mb_addr_normal),
      .i_addr_load_bitrev(w_br_to_mb_addr_reversed),
      .i_re              (w_br_to_mb_tdata_re),
      .i_im              (w_br_to_mb_tdata_im),
      .o_re              (o_tdata_re),
      .o_im              (o_tdata_im),
      .o_index           (o_xk_index),
      .i_wren_1          (w_wr_en_1),
      .i_wr_addr_X       (w_wr_addr_mem_a),
      .i_rd_addr_X       (r_rd_addr_mem_a),
      .i_wren_2          (w_wr_en_2),
      .i_wr_addr_Y       (w_wr_addr_mem_b),
      .i_rd_addr_Y       (r_rd_addr_mem_b),
      .i_xr              (w_calculated_xr),
      .i_xi              (w_calculated_xi),
      .i_yr              (w_calculated_yr),
      .i_yi              (w_calculated_yi),
      .o_xr              (w_stored_xr),
      .o_xi              (w_stored_xi),
      .o_yr              (w_stored_yr),
      .o_yi              (w_stored_yi)
  );
  // Twiddle ROM
  twiddle_rom_wrapper #(
      .DATA_WIDTH(DATA_WIDTH),
      .DATA_DEPTH(NFFT)
  ) twiddle_rom_wrapper_inst (
      .clk   (clk),
      .i_addr(r_rd_addr_twiddle_d2),
      .o_tr  (w_twiddle_tr),
      .o_ti  (w_twiddle_ti)
  );

  // FFT
  butterfly #(
      .DATA_WIDTH (DATA_WIDTH  /* default 16 */),
      .DATA_FORMAT(QFORMAT  /* default 15 */)
  ) butterfly_inst (
      .clk (clk),
      .i_ar(w_stored_xr),
      .i_ai(w_stored_xi),
      .i_br(w_stored_yr),
      .i_bi(w_stored_yi),
      .i_tr(w_twiddle_tr),
      .i_ti(w_twiddle_ti),
      .o_xr(w_calculated_xr),
      .o_xi(w_calculated_xi),
      .o_yr(w_calculated_yr),
      .o_yi(w_calculated_yi)
  );

  // Bit Reversal Unit
  bit_reversal_unit #(
      .DATA_WIDTH     (DATA_WIDTH  /* default 16 */),
      .DATA_DEPTH_LOG2(C_NFFT_LOG2  /* default 11 */)
  ) bit_reversal_unit_inst (
      .clk             (clk),
      .reset           (reset),
      .i_tdata_re      (w_buffer_re_out),
      .i_tdata_im      (w_buffer_im_out),
      .i_tvalid        (r_buffer_tvalid_out),
      .o_tdata_re      (w_br_to_mb_tdata_re),
      .o_tdata_im      (w_br_to_mb_tdata_im),
      .o_taddr_reversed(w_br_to_mb_addr_reversed),
      .o_taddr_normal  (w_br_to_mb_addr_normal),
      .o_tvalid        (w_br_tvalid_out)
  );

  // Input data buffer
  assign w_buffer_re_im_in = {i_tdata_re, i_tdata_im};
  sp_bram #(
      .RAM_WIDTH     (2 * DATA_WIDTH),
      .RAM_DEPTH_BITS(C_NFFT_LOG2  /* default 5 */)
  ) input_buffer_inst (
      .clk   (clk),
      .i_addr(r_input_buf_addr),
      .i_din (w_buffer_re_im_in),
      .i_we  (w_buffer_tvalid_in),
      .o_dout(w_buffer_re_im_out)
  );
  assign w_buffer_re_out = w_buffer_re_im_out[2*DATA_WIDTH-1:DATA_WIDTH];
  assign w_buffer_im_out = w_buffer_re_im_out[DATA_WIDTH-1:0];
endmodule
