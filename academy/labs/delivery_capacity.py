"""假设参数下的容量与成本算术，不是GPU性能预测或云报价。"""
import json
import math


def nonnegative(*values):
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("finite nonnegative numbers required")


def capacity(arrival_rps, mean_service_seconds, target_utilization):
    nonnegative(arrival_rps, mean_service_seconds, target_utilization)
    if not 0 < target_utilization < 1:
        raise ValueError("target utilization must be between zero and one")
    load = arrival_rps * mean_service_seconds
    return {"offered_mean_concurrency": load,
            "serial_workers_lower_estimate": math.ceil(load / target_utilization),
            "scope": "independent_serial_workers_assumption_not_llm_batch_prediction"}


def cost(requests, input_tokens, output_tokens, input_per_million, output_per_million,
         instance_hours, hourly_cost, other_cost):
    nonnegative(requests, input_tokens, output_tokens, input_per_million,
                output_per_million, instance_hours, hourly_cost, other_cost)
    per_request = (input_tokens * input_per_million + output_tokens * output_per_million) / 1_000_000
    fixed = instance_hours * hourly_cost + other_cost
    return {"api_cost": requests * per_request, "self_hosted_cost": fixed,
            "break_even_requests": fixed / per_request if per_request else None,
            "scope": "hypothetical_same_currency_inputs_excludes_unlisted_costs"}


def error_budget(total_requests, success_target):
    nonnegative(total_requests, success_target)
    if success_target > 1:
        raise ValueError("target must not exceed one")
    return {"allowed_bad_requests": math.floor(total_requests * (1 - success_target) + 1e-9),
            "scope": "request_based_budget_not_time_availability"}


def demo():
    return {"capacity": capacity(2, 0.5, 0.5),
            "cost": cost(100_000, 1000, 200, 2, 6, 720, 1, 80),
            "budget": error_budget(10_000, 0.99),
            "warning": "价格均为虚构教学参数；真实方案需要压测、质量约束与实际报价。"}


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
