"""标准库工具调用边界实验：只读、用户隔离、同请求重放。"""
import hashlib
import json


class ToolError(ValueError):
    pass


class ToolRunner:
    def __init__(self):
        self.jobs = {"job-a": {"owner": "learner-a", "status": "completed"},
                     "job-b": {"owner": "learner-b", "status": "queued"}}
        self.cache = {}
        self.executions = 0

    def call(self, principal, request_id, name, arguments):
        if not isinstance(principal, str) or not principal or not isinstance(request_id, str) or not request_id:
            raise ToolError("principal and request_id are required")
        if name != "read_job" or not isinstance(arguments, dict) or set(arguments) != {"job_id"}:
            raise ToolError("unsupported tool or schema")
        job_id = arguments["job_id"]
        if not isinstance(job_id, str):
            raise ToolError("job_id must be a string")
        job = self.jobs.get(job_id)
        if not job or job["owner"] != principal:
            raise ToolError("job unavailable for this principal")
        fingerprint = hashlib.sha256(json.dumps([name, arguments], sort_keys=True).encode()).hexdigest()
        key = (principal, request_id)
        if key in self.cache:
            old_fingerprint, result = self.cache[key]
            if old_fingerprint != fingerprint:
                raise ToolError("request_id reused with different arguments")
            return dict(result)
        self.executions += 1
        result = {"job_id": job_id, "status": job["status"]}
        self.cache[key] = (fingerprint, result)
        return dict(result)


def main():
    runner = ToolRunner()
    arguments = {"job_id": "job-a"}
    first = runner.call("learner-a", "request-1", "read_job", arguments)
    second = runner.call("learner-a", "request-1", "read_job", arguments)
    try:
        runner.call("learner-a", "request-2", "read_job", {"job_id": "job-b"})
    except ToolError as error:
        denied = str(error)
    print(json.dumps({"scope": "single_process_cpu_tool_contract_demo", "first": first,
                      "replay": second, "executions": runner.executions, "denied": denied}, indent=2))


if __name__ == "__main__":
    main()
