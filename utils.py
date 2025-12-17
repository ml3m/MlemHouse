
def print_report(ctrl, res, stats):
    """Print final report"""
    print("\n" + "=" * 50)
    print("SESSION REPORT")
    print("=" * 50)
    
    print("\nMetrics:")
    for k, v in res["metrics"].items():
        print(f"  {v}")
    
    print("\nIssues:")
    issue_summary = ctrl.get_issue_summary()
    total_detected = sum(issue_summary["detected"].values())
    total_resolved = sum(issue_summary["resolved"].values())
    print(f"  Detected: {total_detected}")
    print(f"  Resolved: {total_resolved}")
    print(f"  Active: {issue_summary['active']}")
    
    if res.get("issue_breakdown"):
        print("\n  Breakdown:")
        for issue_type, count in sorted(res["issue_breakdown"].items(), key=lambda x: -x[1]):
            if issue_type != "none":
                print(f"    {issue_type}: {count}")
    
    print("\nData:")
    s = stats.get_stats()
    print(f"  Readings: {res['total_readings']}")
    print(f"  Critical: {len(res['critical_events'])}")
    print(f"  Written: {s['records_written']}")
    print(f"  Rate: {s['rate']:.1f}/s")
    print(f"  Duration: {s['elapsed']:.1f}s")
