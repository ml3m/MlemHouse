
def f_print_report(v_ctrl, v_res, v_stats):
    """Print final report"""
    print("\n" + "=" * 50)
    print("SESSION REPORT")
    print("=" * 50)
    
    print("\nMetrics:")
    for v_k, v_v in v_res["metrics"].items():
        print(f"  {v_v}")
    
    print("\nIssues:")
    v_issue_summary = v_ctrl.get_issue_summary()
    v_total_detected = sum(v_issue_summary["detected"].values())
    v_total_resolved = sum(v_issue_summary["resolved"].values())
    print(f"  Detected: {v_total_detected}")
    print(f"  Resolved: {v_total_resolved}")
    print(f"  Active: {v_issue_summary['active']}")
    
    if v_res.get("issue_breakdown"):
        print("\n  Breakdown:")
        for v_issue_type, v_count in sorted(v_res["issue_breakdown"].items(), key=lambda x: -x[1]):
            if v_issue_type != "none":
                print(f"    {v_issue_type}: {v_count}")
    
    print("\nData:")
    v_s = v_stats.get_stats()
    print(f"  Readings: {v_res['total_readings']}")
    print(f"  Critical: {len(v_res['critical_events'])}")
    print(f"  Written: {v_s['records_written']}")
    print(f"  Rate: {v_s['rate']:.1f}/s")
    print(f"  Duration: {v_s['elapsed']:.1f}s")
