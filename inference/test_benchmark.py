"""统计与配置契约测试；真实 GPU 请求另存 evidence/inference。"""

import unittest
from unittest.mock import patch

import httpx
from benchmark import make_request, request_spec, summarize


class BenchmarkContractTests(unittest.TestCase):
    def fake_request(self, response, engine="vllm", stream=True):
        transport = httpx.MockTransport(lambda request: response)
        client = httpx.Client(transport=transport)
        with patch("benchmark.httpx.Client", return_value=client):
            return make_request(engine, stream=stream)

    def test_sse_usage_and_text_are_collected(self):
        content = (
            'data: {"choices":[{"delta":{"role":"assistant","content":""}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
            'data: {"choices":[],"usage":{"prompt_tokens":1,"completion_tokens":1}}\n\n'
            "data: [DONE]\n\n"
        )
        result = self.fake_request(httpx.Response(200, text=content))
        self.assertTrue(result["ok"])
        self.assertEqual(result["answer"], "hello")
        self.assertEqual(result["output_tokens"], 1)
        self.assertIsNotNone(result["client_first_content_seconds"])

    def test_truncated_stream_is_not_a_success(self):
        content = (
            'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
            'data: {"choices":[],"usage":{"prompt_tokens":1,"completion_tokens":1}}\n\n'
        )
        result = self.fake_request(httpx.Response(200, text=content))
        self.assertFalse(result["ok"])
        self.assertIn("[DONE]", result["stream_error"]["detail"])

    def test_429_response_stays_failed(self):
        result = self.fake_request(
            httpx.Response(429, json={"detail": "busy"}),
            engine="transformers",
            stream=False,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["http_status"], 429)
        self.assertEqual(result["response"]["detail"], "busy")

    def test_failures_do_not_disappear_from_throughput_denominator(self):
        result = summarize(
            [
                {
                    "ok": True,
                    "http_status": 200,
                    "wall_seconds": 2,
                    "output_tokens": 64,
                },
                {"ok": False, "http_status": 429, "wall_seconds": 0.01},
                {"ok": False, "error": "timeout", "wall_seconds": 10},
            ],
            wall=12,
        )
        self.assertEqual(result["requested"], 3)
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["http_429"], 1)
        self.assertAlmostEqual(result["aggregate_output_tokens_per_second"], 64 / 12)
        self.assertEqual(result["p50_success_wall_seconds"], 2)

    def test_all_failed_has_no_fake_latency(self):
        result = summarize([{"ok": False, "http_status": 429}], 0.2)
        self.assertIsNone(result["p95_success_wall_seconds"])
        self.assertEqual(result["aggregate_output_tokens_per_second"], 0)

    def test_greedy_request_matches_baseline_repetition_penalty(self):
        url, request = request_spec("vllm", True)
        self.assertEqual(url, "http://127.0.0.1:18301/v1/chat/completions")
        self.assertEqual(request["temperature"], 0)
        self.assertEqual(request["repetition_penalty"], 1.05)
        self.assertEqual(request["stream_options"], {"include_usage": True})
        _, baseline = request_spec("transformers", False)
        self.assertEqual(request["max_tokens"], baseline["max_new_tokens"])
        self.assertEqual(request["messages"][-1]["content"], baseline["prompt"])


if __name__ == "__main__":
    unittest.main()
