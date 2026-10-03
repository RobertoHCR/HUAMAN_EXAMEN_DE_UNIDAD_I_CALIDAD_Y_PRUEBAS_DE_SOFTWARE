"""Exporta evidencias y exige cero bugs, vulnerabilidades y hotspots totales."""
import json
import os
from pathlib import Path
import httpx


def fetch(endpoint, params):
    headers = {"Authorization": "Bearer " + os.environ["SONAR_TOKEN"]}
    with httpx.Client(base_url="https://sonarcloud.io/api/", timeout=60) as client:
        response = client.get(endpoint, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


def main():
    project = os.environ["SONAR_PROJECT_KEY"]
    report = Path("reports")
    report.mkdir(exist_ok=True)
    issues = fetch("issues/search", {
        "componentKeys": project, "types": "BUG,VULNERABILITY", "resolved": "false", "ps": 100,
    })
    hotspots = fetch("hotspots/search", {"projectKey": project, "ps": 100})
    gate = fetch("qualitygates/project_status", {"projectKey": project})
    evidence = {"issues": issues, "hotspots": hotspots, "quality_gate": gate}
    (report / "sonar.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    issue_total = issues["paging"]["total"]
    hotspot_total = hotspots["paging"]["total"]
    gate_status = gate["projectStatus"]["status"]
    print(f"Bugs/vulnerabilidades: {issue_total}; hotspots: {hotspot_total}; gate: {gate_status}")
    if issue_total or hotspot_total or gate_status != "OK":
        raise SystemExit("Sonar no cumple las condiciones de la entrega. Corrige los hallazgos.")


if __name__ == "__main__":
    main()
