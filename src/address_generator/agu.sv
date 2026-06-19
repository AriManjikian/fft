import fft::*;

module agu #(
    parameter int DATA_DEPTH_LOG2 = 5
) (
    input logic clk,
    input logic i_start,
    output logic o_done,
    output logic o_wr_en,
    output logic [DATA_DEPTH_LOG2-1:0] o_raddr_mem_a,
    output logic [DATA_DEPTH_LOG2-1:0] o_raddr_mem_b,
    output logic [DATA_DEPTH_LOG2-2:0] o_raddr_twiddle
);
  // Parameters
  localparam int C_NUM_LEVELS = $clog2(DATA_DEPTH_LOG2);
  localparam int C_HOLD_CNT_W = $clog2(C_HOLD_COUNT) + 2;
  localparam logic [C_NUM_LEVELS-1:0] LAST_LEVEL = C_NUM_LEVELS'(DATA_DEPTH_LOG2 - 1);
  // State
  typedef enum logic [1:0] {
    IDLE,
    CLEAR,
    RUN,
    DONE
  } CTRL_STATE_t;
  CTRL_STATE_t ctrl_state = IDLE;
  // Counters
  logic [C_NUM_LEVELS-1:0] r_level = '0;
  logic signed [C_HOLD_CNT_W-1:0] r_hold_counter;

  logic w_hold;
  logic r_hold;

  // Addressing
  logic [DATA_DEPTH_LOG2-1:0] r_addr = '0;
  logic [DATA_DEPTH_LOG2-1:0] r_addr_d1 = '0;
  logic [DATA_DEPTH_LOG2-1:0] r_addr_2x = '0;
  logic [DATA_DEPTH_LOG2-1:0] r_addr_2x_plus_1 = '0;
  logic [DATA_DEPTH_LOG2-1:0] r_addr_a = '0;
  logic [DATA_DEPTH_LOG2-1:0] r_addr_b = '0;

  logic [DATA_DEPTH_LOG2-2:0] r_addr_tw = '0;

  logic [DATA_DEPTH_LOG2-1:0] r_tw_bit_mask = '0;

  // Control
  logic w_clear;
  logic r_clear = 1'b0;
  logic [1:0] r_clear_shreg = '0;
  logic r_valid_addr = 1'b0;

  assign o_raddr_mem_a   = r_addr_a;
  assign o_raddr_mem_b   = r_addr_b;
  assign o_raddr_twiddle = r_addr_tw;
  assign o_wr_en         = r_valid_addr;

  function automatic logic [DATA_DEPTH_LOG2-1:0] rotl(input logic [DATA_DEPTH_LOG2-1:0] x,
                                                      input int r);
    r = r % DATA_DEPTH_LOG2;
    return (x << r) | (x >> (DATA_DEPTH_LOG2 - r));
  endfunction

  // FSM
  always_ff @(posedge clk) begin
    o_done <= 1'b0;
    case (ctrl_state)
      IDLE: begin
        if (i_start) ctrl_state <= CLEAR;
      end
      CLEAR: begin
        r_clear_shreg <= {r_clear_shreg[0], 1'b1};
        if (r_clear_shreg[1]) begin
          r_clear_shreg <= '0;
          ctrl_state <= RUN;
        end
      end
      RUN: begin
        if (r_addr[DATA_DEPTH_LOG2-1] && (r_level >= LAST_LEVEL)) begin
          o_done <= 1'b1;
          ctrl_state <= DONE;
        end
      end
      DONE: begin
        if (i_start) ctrl_state <= CLEAR;
      end
      default: begin
        ctrl_state <= IDLE;
      end
    endcase
  end

  assign w_clear = (ctrl_state != RUN);

  // Address Counter
  always_ff @(posedge clk) begin
    if (w_clear || w_hold) begin
      r_addr <= '0;
    end else begin
      if (r_addr[DATA_DEPTH_LOG2-1]) r_addr <= '0;
      else r_addr <= r_addr + 1;
    end
  end

  // Level Counter
  always_ff @(posedge clk) begin
    if (w_clear) begin
      r_level <= '0;
    end else if (r_addr[DATA_DEPTH_LOG2-1]) begin
      if (r_level >= LAST_LEVEL) r_level <= '0;
      else r_level <= r_level + 1;
    end
  end

  // Hold Counter
  always_ff @(posedge clk) begin
    if (r_addr[DATA_DEPTH_LOG2-1]) begin
      r_hold_counter <= C_HOLD_CNT_W'(C_HOLD_COUNT);
    end else if (r_hold_counter[C_HOLD_CNT_W-1] != 1'b1) begin
      r_hold_counter <= r_hold_counter - 1;
    end
  end
  assign w_hold = ~r_hold_counter[C_HOLD_CNT_W-1];

  // Pipeline
  always_ff @(posedge clk) begin
    r_addr_d1        <= r_addr;

    r_addr_2x        <= {r_addr[DATA_DEPTH_LOG2-2:0], 1'b0};
    r_addr_2x_plus_1 <= {r_addr[DATA_DEPTH_LOG2-2:0], 1'b0} + 1;

    r_hold           <= w_hold;
    r_clear          <= w_clear;
    r_valid_addr     <= ~(r_hold | r_clear | w_hold | w_clear);
  end

  // Addr A generator
  // Rotate N(2j, i)
  always_ff @(posedge clk) begin
    if (w_clear) begin
      r_addr_a <= '0;
    end else begin
      r_addr_a <= rotl(r_addr_2x, int'(r_level));
    end
  end

  // Addr B generator
  // Rotate N(2j+1, i)
  always_ff @(posedge clk) begin
    if (w_clear) begin
      r_addr_b <= '0;
    end else begin
      r_addr_b <= rotl(r_addr_2x_plus_1, int'(r_level));
    end
  end

  // Addr Twiddle generator
  // Mask N-1-{level} of j
  always_ff @(posedge clk) begin
    if (w_clear) begin
      r_tw_bit_mask <= '0;
      r_addr_tw     <= '0;
    end else begin
      r_tw_bit_mask[DATA_DEPTH_LOG2-int'(r_level)-1] <= 1'b1;
      r_addr_tw <= r_tw_bit_mask[DATA_DEPTH_LOG2-2:0] & r_addr_d1[DATA_DEPTH_LOG2-2:0];
    end
  end
endmodule
