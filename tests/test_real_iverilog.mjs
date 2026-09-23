import { compile, simulate } from '@veriflow/iverilog-wasm';

const validUserCode = `
module mux_4to1 (
    input  wire [3:0] d,
    input  wire [1:0] sel,
    output reg        y
);

    always @(*) begin
        case (sel)
            2'b00: y = d[0];
            2'b01: y = d[1];
            2'b10: y = d[2];
            2'b11: y = d[3];
            default: y = 1'b0;
        endcase
    end

endmodule
`;

const testbench = `
module tb_mux;
    reg [3:0] d;
    reg [1:0] sel;
    wire y;

    mux_4to1 dut (.d(d), .sel(sel), .y(y));

    initial begin
        d = 4'b1010;
        sel = 2'b00; #5;
        if (y !== 1'b0) $display("FAIL 00"); else $display("PASS 00");
        sel = 2'b01; #5;
        if (y !== 1'b1) $display("FAIL 01"); else $display("PASS 01");
        sel = 2'b10; #5;
        if (y !== 1'b0) $display("FAIL 10"); else $display("PASS 10");
        sel = 2'b11; #5;
        if (y !== 1'b1) $display("FAIL 11"); else $display("PASS 11");
        $display("ALL_DONE");
        $finish;
    end
endmodule
`;

console.log("Simulating valid code with real Icarus Verilog testbench...");
const simResult = await simulate({
  files: [
    { path: 'solution.v', data: validUserCode },
    { path: 'testbench.v', data: testbench }
  ],
  sources: ['testbench.v', 'solution.v'],
  generation: '2012',
});

console.log("Sim success:", simResult.success);
console.log("Sim stdout:\n" + simResult.stdout);

