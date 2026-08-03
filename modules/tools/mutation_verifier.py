"""
Mutation Verification Guard — prevents false completion claims.
Verifies writes, pushes, installs, and state changes actually took effect.
"""
import os, hashlib, subprocess, json


class MutationVerifier:
    """Verify mutations actually took effect. Never trust exit code alone."""

    @staticmethod
    def file_created(path: str) -> dict:
        exists = os.path.exists(path)
        return {
            "operation": "create",
            "path": path,
            "verified": exists,
            "evidence": f"file exists: {exists}, size: {os.path.getsize(path) if exists else 0}",
            "failure": None if exists else f"file not found at {path}",
        }

    @staticmethod
    def file_modified(path: str, before_hash: str = None) -> dict:
        if not os.path.exists(path):
            return {"operation": "modify", "path": path, "verified": False, "evidence": "file does not exist"}
        try:
            current = hashlib.sha256(open(path, "rb").read()).hexdigest()
        except (OSError, PermissionError) as e:
            return {"operation": "modify", "path": path, "verified": False, "evidence": str(e)[:200]}

        if before_hash is None:
            # No comparison evidence — cannot confirm modification
            return {
                "operation": "modify",
                "path": path,
                "verified": False,
                "status": "UNKNOWN",
                "evidence": "INSUFFICIENT_EVIDENCE: no before_hash provided for comparison",
                "sha256_current": current[:16],
            }

        if current == before_hash:
            return {"operation": "modify", "path": path, "verified": False, "evidence": "content unchanged"}
        return {
            "operation": "modify",
            "path": path,
            "verified": True,
            "evidence": f"content changed: {before_hash[:12]} → {current[:12]}",
        }

    @staticmethod
    def git_remote_contains(local_sha: str = None, remote: str = "origin", branch: str = "main") -> dict:
        """Verify local commit is an ancestor/reachable from remote branch."""
        try:
            fetch = subprocess.run(["git", "fetch", remote, branch], capture_output=True, text=True, timeout=15)
            if fetch.returncode != 0:
                return {"verified": False, "evidence": f"fetch failed: {fetch.stderr[:200]}"}

            if local_sha is None:
                local_sha = subprocess.run(["git", "rev-parse", "HEAD"],
                                           capture_output=True, text=True, timeout=5).stdout.strip()

            # Check if remote contains this commit
            merge_base = subprocess.run(
                ["git", "merge-base", "--is-ancestor", local_sha, f"{remote}/{branch}"],
                capture_output=True, timeout=10
            )
            contained = merge_base.returncode == 0
            return {
                "operation": "remote_contains",
                "verified": contained,
                "evidence": f"local={local_sha[:12]} reachable from {remote}/{branch}: {contained}",
            }
        except (subprocess.TimeoutExpired, OSError) as e:
            return {"verified": False, "evidence": str(e)[:200]}

    @staticmethod
    def git_head_matches(remote: str = "origin", branch: str = "main", local_sha: str = None) -> dict:
        """Verify remote HEAD exactly matches expected SHA."""
        try:
            fetch = subprocess.run(["git", "fetch", remote, branch], capture_output=True, text=True, timeout=15)
            if fetch.returncode != 0:
                return {"verified": False, "evidence": f"fetch failed: {fetch.stderr[:200]}"}

            if local_sha is None:
                local_sha = subprocess.run(["git", "rev-parse", "HEAD"],
                                           capture_output=True, text=True, timeout=5).stdout.strip()

            remote_sha = subprocess.run(
                ["git", "rev-parse", f"{remote}/{branch}"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()

            match = local_sha == remote_sha
            return {
                "operation": "head_match",
                "verified": match,
                "evidence": f"local={local_sha[:12]} remote({remote}/{branch})={remote_sha[:12]} match={match}",
            }
        except (subprocess.TimeoutExpired, OSError) as e:
            return {"verified": False, "evidence": str(e)[:200]}

    @staticmethod
    def git_pushed(remote: str = "origin", branch: str = "main", local_sha: str = None) -> dict:
        """Combined check: REMOTE_CONTAINS_COMMIT is the primary push verification."""
        contains = MutationVerifier.git_remote_contains(local_sha, remote, branch)
        head = MutationVerifier.git_head_matches(remote, branch, local_sha)
        return {
            "operation": "push",
            "remote_contains": contains["verified"],
            "head_matches": head["verified"],
            "verified": contains["verified"],
            "evidence": f"contains={contains['verified']} head_match={head['verified']}",
        }

    @staticmethod
    def executable_works(executable: str) -> dict:
        path_r = subprocess.run(["which", executable], capture_output=True, text=True, timeout=5)
        if path_r.returncode != 0:
            return {"operation": "install", "executable": executable,
                    "verified": False, "status": "NOT_INSTALLED", "evidence": "not in PATH"}

        # Try --version first, then --help, then just path existence
        for flag in ["--version", "-v", "-V", "--help"]:
            v = subprocess.run([executable, flag], capture_output=True, text=True, timeout=5)
            if v.returncode == 0 and v.stdout.strip():
                return {"operation": "install", "executable": executable,
                        "verified": True, "status": "FUNCTIONAL",
                        "evidence": v.stdout.strip().split("\n")[0], "path": path_r.stdout.strip()}

        # Fallback: just installed but not necessarily functional
        return {"operation": "install", "executable": executable,
                "verified": False, "status": "INSTALLED_NOT_TESTED",
                "evidence": f"found at {path_r.stdout.strip()} but --version not available", "path": path_r.stdout.strip()}

    @staticmethod
    def container_running(container_name: str) -> dict:
        r = subprocess.run(
            ["docker", "ps", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}  {{.Status}}"],
            capture_output=True, text=True, timeout=10
        )
        running = container_name in r.stdout
        return {
            "operation": "container",
            "name": container_name,
            "verified": running,
            "evidence": r.stdout.strip() if running else f"container '{container_name}' not running",
        }

    @staticmethod
    def verify(task: str, claim: str, **kwargs) -> dict:
        verifiers = {
            "file_created": MutationVerifier.file_created,
            "file_modified": MutationVerifier.file_modified,
            "git_pushed": MutationVerifier.git_pushed,
            "git_remote_contains": MutationVerifier.git_remote_contains,
            "git_head_matches": MutationVerifier.git_head_matches,
            "executable_works": MutationVerifier.executable_works,
            "container_running": MutationVerifier.container_running,
        }
        v = verifiers.get(claim)
        if not v:
            return {"task": task, "claim": claim, "verified": False, "evidence": f"unknown verifier: {claim}"}
        result = v(**kwargs)
        result["task"] = task
        result["claim"] = claim
        return result
