module bit_reversal_unit #(
    parameter int DATA_WIDTH = 16,
    parameter int DATA_DEPTH_LOG2 = 11
) (
    input clk,
    input reset,
    input logic [DATA_WIDTH-1:0] i_tdata_re,
    input logic [DATA_WIDTH-1:0] i_tdata_im,
    input logic i_tvalid,
    output logic [DATA_WIDTH-1:0] o_tdata_re,
    output logic [DATA_WIDTH-1:0] o_tdata_im,
    output logic [DATA_DEPTH_LOG2-1:0] o_taddr_reversed,
    output logic [DATA_DEPTH_LOG2-1:0] o_taddr_normal,
    output logic o_tvalid
);

  function automatic logic [DATA_DEPTH_LOG2-1:0] bit_reverse_vector(
      input logic [DATA_DEPTH_LOG2-1:0] a);

    logic [DATA_DEPTH_LOG2-1:0] v_result;

    for (int i = 0; i < DATA_DEPTH_LOG2; i++) begin
      v_result[i] = a[i];
    end

    return v_result;
  endfunction

  logic unsigned [DATA_DEPTH_LOG2-1:0] r_addr;

  always_ff @(posedge clk) begin
    o_tvalid <= 0;
    if (reset == '1) begin
      r_addr <= '0;
    end else if (i_tvalid == '1) begin
      r_addr           <= r_addr + 1;
      o_tdata_re       <= i_tdata_re;
      o_tdata_im       <= i_tdata_im;
      o_taddr_reversed <= bit_reverse_vector(r_addr);
      o_taddr_normal   <= r_addr;
      o_tvalid         <= '1;
    end
  end
endmodule
