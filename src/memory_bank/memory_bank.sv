module memory_bank #(
    parameter int DATA_WIDTH = fft::DATA_WIDTH,
    parameter int DATA_DEPTH_LOG2 = $clog2(fft::DATA_DEPTH)
) (
    input logic clk,

    input logic i_wren_re_A,
    input logic i_wren_re_B,
    input logic [DATA_DEPTH_LOG2-1:0] i_addr_re_A,
    input logic [DATA_DEPTH_LOG2-1:0] i_addr_re_B,
    input logic [DATA_WIDTH-1:0] i_data_re_A,
    input logic [DATA_WIDTH-1:0] i_data_re_B,
    output logic [DATA_WIDTH-1:0] o_data_re_A,
    output logic [DATA_WIDTH-1:0] o_data_re_B,

    input logic i_wren_im_A,
    input logic i_wren_im_B,
    input logic [DATA_DEPTH_LOG2-1:0] i_addr_im_A,
    input logic [DATA_DEPTH_LOG2-1:0] i_addr_im_B,
    input logic [DATA_WIDTH-1:0] i_data_im_A,
    input logic [DATA_WIDTH-1:0] i_data_im_B,
    output logic [DATA_WIDTH-1:0] o_data_im_A,
    output logic [DATA_WIDTH-1:0] o_data_im_B
);

  tpd_bram #(
      .DATA_DEPTH(2 ** DATA_DEPTH_LOG2),
      .DATA_WIDTH(DATA_WIDTH  /* default 16 */)
  ) mem_real_inst (
      .i_clka (clk),
      .i_clkb (clk),
      .i_ena  ('1),
      .i_enb  ('1),
      .i_wea  (i_wren_re_A),
      .i_web  (i_wren_re_B),
      .i_addra(i_addr_re_A),
      .i_addrb(i_addr_re_B),
      .i_dia  (i_data_re_A),
      .i_dib  (i_data_re_B),
      .o_doa  (o_data_re_A),
      .o_dob  (o_data_re_B)
  );


  tpd_bram #(
      .DATA_DEPTH(2 ** DATA_DEPTH_LOG2),
      .DATA_WIDTH(DATA_WIDTH  /* default 16 */)
  ) mem_imag_inst (
      .i_clka (clk),
      .i_clkb (clk),
      .i_ena  ('1),
      .i_enb  ('1),
      .i_wea  (i_wren_im_A),
      .i_web  (i_wren_im_B),
      .i_addra(i_addr_im_A),
      .i_addrb(i_addr_im_B),
      .i_dia  (i_data_im_A),
      .i_dib  (i_data_im_B),
      .o_doa  (o_data_im_A),
      .o_dob  (o_data_im_B)
  );

endmodule
