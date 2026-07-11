module tpd_bram #(
    parameter int DATA_DEPTH = fft::DATA_DEPTH,
    parameter int DATA_WIDTH = fft::DATA_WIDTH
) (
    input logic i_Clka,
    input logic i_Clkb,
    input logic i_ena,
    input logic i_enb,
    input logic i_wea,
    input logic i_web,
    input logic [$clog2(DATA_DEPTH)-1:0] i_addra,
    input logic [$clog2(DATA_DEPTH)-1:0] i_addrb,
    input logic [DATA_WIDTH-1:0] i_dia,
    input logic [DATA_WIDTH-1:0] i_dib,
    output logic [DATA_WIDTH-1:0] o_doa,
    output logic [DATA_WIDTH-1:0] o_dob
);
  logic [DATA_WIDTH-1:0] ram[DATA_DEPTH];
  always @(posedge i_Clka) begin
    if (i_ena) begin
      o_doa <= ram[i_addra];
      if (i_wea) begin
        ram[i_addra] <= i_dia;
      end
    end
  end

  always @(posedge i_Clkb) begin
    if (i_enb) begin
      o_dob <= ram[i_addrb];
      if (i_web) begin
        ram[i_addrb] <= i_dib;
      end
    end
  end
endmodule
