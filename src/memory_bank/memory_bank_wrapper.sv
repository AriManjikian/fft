module memory_bank_wrapper #(
    parameter int DATA_WIDTH = fft::DATA_WIDTH,
    parameter int DATA_DEPTH_LOG2 = $clog2(fft::DATA_DEPTH)
) (
    input logic clk,
    // Control
    input logic i_bank_select,
    input logic i_load_unload,
    input logic [DATA_DEPTH_LOG2-1:0] i_addr_load,
    input logic [DATA_DEPTH_LOG2-1:0] i_addr_load_bitrev,
    // I/O
    input logic [DATA_WIDTH-1:0] i_re,
    input logic [DATA_WIDTH-1:0] i_im,
    output logic [DATA_WIDTH-1:0] o_re,
    output logic [DATA_WIDTH-1:0] o_im,
    output logic [DATA_DEPTH_LOG2-1:0] o_index,
    // R/W
    input logic i_wren_1,
    input logic [DATA_DEPTH_LOG2-1:0] i_wr_addr_X,
    input logic [DATA_DEPTH_LOG2-1:0] i_rd_addr_X,
    input logic i_wren_2,
    input logic [DATA_DEPTH_LOG2-1:0] i_wr_addr_Y,
    input logic [DATA_DEPTH_LOG2-1:0] i_rd_addr_Y,
    // BFU
    input logic [DATA_WIDTH-1:0] i_xr,
    input logic [DATA_WIDTH-1:0] i_xi,
    input logic [DATA_WIDTH-1:0] i_yr,
    input logic [DATA_WIDTH-1:0] i_yi,
    output logic [DATA_WIDTH-1:0] o_xr,
    output logic [DATA_WIDTH-1:0] o_xi,
    output logic [DATA_WIDTH-1:0] o_yr,
    output logic [DATA_WIDTH-1:0] o_yi
);
  // Bank 1
  logic [DATA_DEPTH_LOG2-1:0] r_addr_1_X;
  logic [DATA_DEPTH_LOG2-1:0] r_addr_1_Y;
  logic [DATA_WIDTH-1:0] r_data_in_1_xr;
  logic [DATA_WIDTH-1:0] r_data_in_1_xi;
  logic [DATA_WIDTH-1:0] r_data_in_1_yr;
  logic [DATA_WIDTH-1:0] r_data_in_1_yi;
  logic [DATA_WIDTH-1:0] w_data_out_1_xr;
  logic [DATA_WIDTH-1:0] w_data_out_1_xi;
  logic [DATA_WIDTH-1:0] w_data_out_1_yr;
  logic [DATA_WIDTH-1:0] w_data_out_1_yi;
  logic r_wren_1_X = 1'b0;
  logic r_wren_1_Y = 1'b0;

  // Bank 2
  logic [DATA_DEPTH_LOG2-1:0] r_addr_2_X;
  logic [DATA_DEPTH_LOG2-1:0] r_addr_2_Y;
  logic [DATA_WIDTH-1:0] r_data_in_2_xr;
  logic [DATA_WIDTH-1:0] r_data_in_2_xi;
  logic [DATA_WIDTH-1:0] r_data_in_2_yr;
  logic [DATA_WIDTH-1:0] r_data_in_2_yi;
  logic [DATA_WIDTH-1:0] w_data_out_2_xr;
  logic [DATA_WIDTH-1:0] w_data_out_2_xi;
  logic [DATA_WIDTH-1:0] w_data_out_2_yr;
  logic [DATA_WIDTH-1:0] w_data_out_2_yi;
  logic r_wren_2_X = 1'b0;
  logic r_wren_2_Y = 1'b0;

  // Output
  logic r_last_write_mem_1 = 1'b0;
  logic [1:0] r_load_unload_pipeline = '0;
  logic [DATA_DEPTH_LOG2-1:0] r_index_out_pipeline[0:1] = '{default: '0};

  // addr mux
  always_ff @(posedge clk) begin
    if (i_bank_select) begin
      // Read Bank 1
      r_addr_1_X <= i_rd_addr_X;
      r_addr_1_Y <= i_rd_addr_Y;
      // Write Bank 2
      r_addr_2_X <= i_wr_addr_X;
      r_addr_2_Y <= i_wr_addr_Y;
    end else begin
      // Read Bank 2
      r_addr_2_X <= i_rd_addr_X;
      r_addr_2_Y <= i_rd_addr_Y;
      // Write Bank 1
      r_addr_1_X <= i_wr_addr_X;
      r_addr_1_Y <= i_wr_addr_Y;
    end
    if (i_load_unload) begin
      if (r_last_write_mem_1) begin
        // Load
        r_addr_2_X <= i_addr_load_bitrev;
        // Unload
        r_addr_1_X <= i_addr_load;
      end else begin
        // Load
        r_addr_1_X <= i_addr_load_bitrev;
        // Unload
        r_addr_2_X <= i_addr_load;
      end
    end
  end

  // data_in mux
  always_ff @(posedge clk) begin
    r_data_in_1_xr <= i_xr;
    r_data_in_1_xi <= i_xi;
    r_data_in_1_yr <= i_yr;
    r_data_in_1_yi <= i_yi;
    r_data_in_2_xr <= i_xr;
    r_data_in_2_xi <= i_xi;
    r_data_in_2_yr <= i_yr;
    r_data_in_2_yi <= i_yi;

    if (i_load_unload) begin
      if (r_last_write_mem_1) begin
        r_data_in_2_xr <= i_re;
        r_data_in_2_xi <= i_im;
        r_data_in_2_yr <= '0;
        r_data_in_2_yi <= '0;
      end else begin
        r_data_in_1_xr <= i_re;
        r_data_in_1_xi <= i_im;
        r_data_in_1_yr <= '0;
        r_data_in_1_yi <= '0;
      end
    end
  end

  // data_out mux
  always_ff @(posedge clk) begin
    if (i_bank_select) begin
      o_xr <= w_data_out_1_xr;
      o_xi <= w_data_out_1_xi;
      o_yr <= w_data_out_1_yr;
      o_yi <= w_data_out_1_yi;
    end else begin
      o_xr <= w_data_out_2_xr;
      o_xi <= w_data_out_2_xi;
      o_yr <= w_data_out_2_yr;
      o_yi <= w_data_out_2_yi;
    end
    if (r_load_unload_pipeline[$high(r_load_unload_pipeline)]) begin
      o_index <= r_index_out_pipeline[$high(r_index_out_pipeline)-1];

      if (r_last_write_mem_1) begin
        o_re <= w_data_out_1_xr;
        o_im <= -w_data_out_1_xi;
      end else begin
        o_re <= w_data_out_2_xr;
        o_im <= -w_data_out_2_xi;
      end
    end
  end

  // data_wren mux
  always_ff @(posedge clk) begin
    r_wren_1_X <= i_wren_1;
    r_wren_1_Y <= i_wren_1;
    r_wren_2_X <= i_wren_2;
    r_wren_2_Y <= i_wren_2;
    if (i_load_unload) begin
      if (r_last_write_mem_1) begin
        r_wren_2_X <= i_load_unload;
      end else begin
        r_wren_1_X <= i_load_unload;
      end
    end
  end

  // track_last_write
  always_ff @(posedge clk) begin
    if (r_wren_1_Y) begin
      r_last_write_mem_1 <= 1'b1;
    end else if (r_wren_2_Y) begin
      r_last_write_mem_1 <= 1'b0;
    end
  end

  // pipeline
  always_ff @(posedge clk) begin
    r_load_unload_pipeline  <= {r_load_unload_pipeline[0], i_load_unload};

    r_index_out_pipeline[0] <= r_index_out_pipeline[1];
    r_index_out_pipeline[1] <= i_addr_load;
  end

  // Bank 1
  memory_bank #(
      .DATA_WIDTH     (DATA_WIDTH  /* default 16 */),
      .DATA_DEPTH_LOG2(DATA_DEPTH_LOG2  /* default 5 */)
  ) memory_bank_1_inst (
      .clk        (clk),
      .i_wren_re_A(r_wren_1_X),
      .i_wren_re_B(r_wren_1_Y),
      .i_addr_re_A(r_addr_1_X),
      .i_addr_re_B(r_addr_1_Y),
      .i_data_re_A(r_data_in_1_xr),
      .i_data_re_B(r_data_in_1_yr),
      .o_data_re_A(w_data_out_1_xr),
      .o_data_re_B(w_data_out_1_yr),
      .i_wren_im_A(r_wren_1_X),
      .i_wren_im_B(r_wren_1_Y),
      .i_addr_im_A(r_addr_1_X),
      .i_addr_im_B(r_addr_1_Y),
      .i_data_im_A(r_data_in_1_xi),
      .i_data_im_B(r_data_in_1_yi),
      .o_data_im_A(w_data_out_1_xi),
      .o_data_im_B(w_data_out_1_yi)
  );

  // Bank 2
  memory_bank #(
      .DATA_WIDTH     (DATA_WIDTH  /* default 16 */),
      .DATA_DEPTH_LOG2(DATA_DEPTH_LOG2  /* default 5 */)
  ) memory_bank_2_inst (
      .clk        (clk),
      .i_wren_re_A(r_wren_2_X),
      .i_wren_re_B(r_wren_2_Y),
      .i_addr_re_A(r_addr_2_X),
      .i_addr_re_B(r_addr_2_Y),
      .i_data_re_A(r_data_in_2_xr),
      .i_data_re_B(r_data_in_2_yr),
      .o_data_re_A(w_data_out_2_xr),
      .o_data_re_B(w_data_out_2_yr),
      .i_wren_im_A(r_wren_2_X),
      .i_wren_im_B(r_wren_2_Y),
      .i_addr_im_A(r_addr_2_X),
      .i_addr_im_B(r_addr_2_Y),
      .i_data_im_A(r_data_in_2_xi),
      .i_data_im_B(r_data_in_2_yi),
      .o_data_im_A(w_data_out_2_xi),
      .o_data_im_B(w_data_out_2_yi)
  );

endmodule
