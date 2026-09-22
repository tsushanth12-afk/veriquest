-- ==========================================================================
-- VeriQuest Seed Migration: Development Demo Challenge
--
-- Single proof-of-concept challenge: "Two-Input AND Gate"
-- Category: "Development Demo"
-- All other curriculum will be created by admins via the Admin API.
-- ==========================================================================

DO $$
DECLARE
    v_challenge_id UUID := 'c0000000-0000-0000-0000-000000000001'::UUID;
BEGIN
    -- 1. Insert or update challenge metadata
    INSERT INTO public.challenges (
        id,
        slug,
        title,
        description,
        category,
        difficulty,
        level_number,
        xp_reward,
        estimated_minutes,
        starter_code,
        input_description,
        output_description,
        constraints,
        public_examples,
        io_pins,
        hints,
        learning_objective,
        is_published,
        validation_status,
        validated_at,
        published_at
    )
    VALUES (
        v_challenge_id,
        'and-gate-demo',
        'Two-Input AND Gate',
        'Implement a basic 2-input AND gate in Verilog HDL. The output `y` must be high (`1`) if and only if both inputs `a` and `b` are high (`1`). When either input is low (`0`), the output must be low (`0`).',
        'Development Demo',
        'Easy',
        1,
        40,
        10,
        E'// Design a 2-input AND gate\n// Output y should be 1 if and only if both a and b are 1.\n\nmodule and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n\n    // Enter your combinational logic here\n\nendmodule\n',
        'Two 1-bit input wire signals: `a` and `b`.',
        'A single 1-bit output wire signal: `y` representing `a AND b`.',
        '["Combinational logic only (no sequential clock/registers)", "Propagation delay: instantaneous (zero-delay simulation)"]'::JSONB,
        '[
            {"input": "a = 0, b = 0", "output": "y = 0", "explanation": "0 & 0 = 0"},
            {"input": "a = 0, b = 1", "output": "y = 0", "explanation": "0 & 1 = 0"},
            {"input": "a = 1, b = 0", "output": "y = 0", "explanation": "1 & 0 = 0"},
            {"input": "a = 1, b = 1", "output": "y = 1", "explanation": "1 & 1 = 1"}
        ]'::JSONB,
        '[
            {"name": "a", "direction": "input", "width": 1, "description": "First boolean operand"},
            {"name": "b", "direction": "input", "width": 1, "description": "Second boolean operand"},
            {"name": "y", "direction": "output", "width": 1, "description": "Boolean AND product"}
        ]'::JSONB,
        '[
            "In Verilog, continuous assignments use the `assign` keyword: `assign y = a & b;`",
            "The `&` operator performs a bitwise boolean AND operation."
        ]'::JSONB,
        'Learn fundamental continuous assignment and boolean operators in Verilog HDL.',
        TRUE,
        'published',
        NOW(),
        NOW()
    )
    ON CONFLICT (slug) DO UPDATE SET
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        category = EXCLUDED.category,
        difficulty = EXCLUDED.difficulty,
        level_number = EXCLUDED.level_number,
        xp_reward = EXCLUDED.xp_reward,
        starter_code = EXCLUDED.starter_code,
        input_description = EXCLUDED.input_description,
        output_description = EXCLUDED.output_description,
        constraints = EXCLUDED.constraints,
        public_examples = EXCLUDED.public_examples,
        io_pins = EXCLUDED.io_pins,
        hints = EXCLUDED.hints,
        learning_objective = EXCLUDED.learning_objective,
        is_published = EXCLUDED.is_published,
        validation_status = EXCLUDED.validation_status,
        updated_at = NOW();

    -- Retrieve ID in case slug already existed with a different UUID
    SELECT id INTO v_challenge_id FROM public.challenges WHERE slug = 'and-gate-demo';

    -- 2. Insert or update private challenge secrets
    INSERT INTO private.challenge_secrets (
        challenge_id,
        official_solution,
        hidden_testbench,
        evaluator_type,
        execution_profile,
        private_notes
    )
    VALUES (
        v_challenge_id,
        E'// Official Reference Solution: Two-Input AND Gate\nmodule and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n\n    assign y = a & b;\n\nendmodule\n',
        E'`timescale 1ns/1ps\n\nmodule tb_and_gate;\n    reg a;\n    reg b;\n    wire y;\n    integer passed = 0;\n    integer failed = 0;\n\n    // Instantiate Unit Under Test\n    and_gate uut (\n        .a(a),\n        .b(b),\n        .y(y)\n    );\n\n    task check_case;\n        input exp_y;\n        input [1:0] in_vec;\n        begin\n            #1;\n            if (y === exp_y) begin\n                $display("TEST CASE PASS: a=%b b=%b -> y=%b (expected %b)", a, b, y, exp_y);\n                passed = passed + 1;\n            end else begin\n                $display("TEST CASE FAIL: a=%b b=%b -> y=%b (expected %b)", a, b, y, exp_y);\n                failed = failed + 1;\n            end\n        end\n    endtask\n\n    initial begin\n        // Test all combinations of 2-input truth table\n        a = 0; b = 0;\n        check_case(1''b0, 2''b00);\n\n        a = 0; b = 1;\n        check_case(1''b0, 2''b01);\n\n        a = 1; b = 0;\n        check_case(1''b0, 2''b10);\n\n        a = 1; b = 1;\n        check_case(1''b1, 2''b11);\n\n        $display("--- SUMMARY ---");\n        $display("TOTAL: 4");\n        $display("PASSED: %0d", passed);\n        $display("FAILED: %0d", failed);\n\n        if (failed == 0) begin\n            $display("VERIQUEST_STATUS: ACCEPTED");\n            $finish(0);\n        end else begin\n            $display("VERIQUEST_STATUS: WRONG_ANSWER");\n            $finish(1);\n        end\n    end\nendmodule\n',
        'hidden_testbench',
        '{
            "timeout_ms": 5000,
            "memory_mb": 256,
            "cpu_limit": "1.0",
            "pids_limit": 64,
            "max_output_bytes": 65536
        }'::JSONB,
        'Demonstration reference solution and comprehensive 4-case truth-table testbench for platform validation.'
    )
    ON CONFLICT (challenge_id) DO UPDATE SET
        official_solution = EXCLUDED.official_solution,
        hidden_testbench = EXCLUDED.hidden_testbench,
        evaluator_type = EXCLUDED.evaluator_type,
        execution_profile = EXCLUDED.execution_profile,
        private_notes = EXCLUDED.private_notes,
        updated_at = NOW();

END $$;
