"""Assemble the scientific supplement and annotated source-data upload."""
import argparse
import hashlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from build_paper import expand


SUPPLEMENTARY_DATA = {'Supplementary_Figure_1': ('Exact upper-table assignment on 512 native channels at 16 users; separate profiles.', ['sim_exact_dp_profiles']), 'Supplementary_Figure_2': ('Four gap components and the fixed-action selectivity experiment; matchings are distinguished.', ['sim_sensitivity_cells', 'sim_fixed_policy_selectivity']), 'Supplementary_Figure_3': ('Within-profile primary gap ECDFs, with late outcomes retained in the denominator.', ['sim_primary_blocks']), 'Supplementary_Figure_4': ('Primary stage times and the separate shuffled-order timing cohort.', ['sim_primary_blocks', 'sim_shuffled_load']), 'Supplementary_Figure_5': ('Ray-scene geometry and four-term gap components.', ['physics_geometry']), 'Supplementary_Figure_6': ('Stationary pilot-cost outcomes and exact two-sided 95% binomial intervals.', ['physics_horizon_intervals']), 'Supplementary_Figure_7': ('Archived RENEW denominators and nested-size sensitivity.', ['hardware_renew_frames', 'hardware_renew_nested', 'hardware_renew_totals']), 'Supplementary_Figure_8': ('Argos spatial overlaps and qualified-frame comparisons.', ['hardware_argos_frames', 'hardware_argos_pairs', 'hardware_argos_hash_checks']), 'Supplementary_Table_1': ('Ten closest studies, their model and guarantee scope.', ['closest_studies']), 'Supplementary_Table_2': ('Gaussian order-statistic integration and rigorous outward enclosures.', ['table_s1_gaussian']), 'Supplementary_Table_3': ('Archived primary gaps and timing stages by profile.', ['sim_primary_profiles', 'sim_primary_timed_calls']), 'Supplementary_Table_4': ('Seed selection and one-component swaps.', ['sim_seed_selection', 'sim_component_swaps', 'sim_validation_records']), 'Supplementary_Table_5': ('Full sensitivity grid; timing cohorts are explicitly separate.', ['sim_sensitivity_summary', 'sim_sensitivity_cells', 'sim_sensitivity_methods']), 'Supplementary_Table_6': ('Absolute rates and a common per-topology best ceiling. The matching control includes power refinement.', ['reviewer_absolute_rates', 'reviewer_absolute_rate_summary']), 'Supplementary_Table_7': ('New three-repeat, iteration-matched deterministic control; equal iteration counts do not imply equal wall times.', ['reviewer_compute_calls', 'reviewer_compute_blocks', 'reviewer_compute_summary']), 'Supplementary_Table_8': ('Enclosing ranges for upper slack and action suboptimality. K16 table DP is not a continuous physical optimum.', ['reviewer_gap_decomposition', 'reviewer_gap_decomposition_summary']), 'Supplementary_Table_9': ('Ray geometry and gap components across guarded tiles.', ['physics_geometry_summary']), 'Supplementary_Table_10': ('O1 fixed-depth refinement-budget sweep, 64 tiles.', ['reviewer_refinement_sweep', 'reviewer_refinement_summary']), 'Supplementary_Table_11': ('Stationary net-rate fractions with exact binomial intervals.', ['reviewer_horizon_intervals']), 'Supplementary_Table_12': ('Original RENEW quality and capture denominators.', ['hardware_renew_totals', 'hardware_renew_nested']), 'Supplementary_Table_13': ('Chronological LTS1-to-LTS2 calibration/test evaluation and all 90 fixed-equal-power labelled schedules. Observed later pilots are not latent truth.', ['reviewer_hardware_calibration_HUB', 'reviewer_hardware_calibration_LO']), 'Supplementary_Table_14': ('Argos recording-level overlap and window-integrity summaries.', ['hardware_argos_frames', 'hardware_argos_pairs', 'hardware_argos_hash_checks']), 'Supplementary_Table_15': ('Outward numerical-kernel root and leaf evaluation counts.', ['table_s2_kernel_counts']), 'Supplementary_Table_16': ('Separate CPU verification counts.', ['hardware_audit_counts'])}


SUPPLEMENTARY_DATA.update({
    'Supplementary_Table_6': ('Absolute rates, own and common verified ceilings, and paired threshold counts by channel profile.',
        ['reviewer_absolute_rates', 'reviewer_absolute_rate_summary', 'round2_achieved_rate_comparison', 'action_common_ceiling_counts']),
    'Supplementary_Table_7': ('Three-repeat paired iteration and median-time-budget controls, exact discordant counts and timing-only pilot.',
        ['reviewer_compute_calls', 'reviewer_compute_blocks', 'reviewer_compute_summary',
         'round2_iteration_paired_tests', 'round2_latency_increments', 'round2_time_budget_pilot',
         'round2_time_control_calls', 'round2_time_control_blocks', 'round2_time_control_summary', 'round2_time_control_paired_tests']),
    'Supplementary_Table_8': ('Means, medians and endpoint quartiles of physical brackets; separate exact integer-table reference.',
        ['reviewer_gap_decomposition', 'round2_decomposition_distribution', 'round2_integer_table_reference', 'action_fixed_filter_checks', 'action_two_user_root_widths']),
    'Supplementary_Table_10': ('O1 table-entry diagnostics, selected-entry partition depths, and resolved two/four-user continuous references.',
        ['reviewer_refinement_sweep', 'reviewer_refinement_summary', 'round2_o1_budget_entries',
         'round2_o1_depth', 'round2_o1_depth_summary', 'round2_o1_small_references']),
    'Supplementary_Table_13': ('Raw and phase-invariant chronological calibration, per-user phase diagnostics and all 90 early fixed-power schedules.',
        ['reviewer_hardware_calibration_HUB', 'reviewer_hardware_calibration_LO',
         'round2_hardware_phase_HUB', 'round2_hardware_phase_LO',
         'round2_hardware_comparison_HUB', 'round2_hardware_comparison_LO',
         'round2_hardware_phase_rotations_HUB', 'round2_hardware_phase_rotations_LO'])
})

SUPPLEMENTARY_DATA['Supplementary_Table_10'][1].append('round3_o1_binding_bounds')
SUPPLEMENTARY_DATA['Supplementary_Table_13'][1].extend([
    'round3_hardware_scale_summary', *[
        f'round3_hardware_scale_{kind}_{mode}'
        for kind in ('frames', 'stream_tone') for mode in ('HUB', 'LO')]])


def annotated(name, description, files):
    chunks = [name.replace("_", " ") + " source data", description,
              "UTF-8 CSV blocks retain source precision. Rates are bit/s/Hz unless explicitly labelled aggregate nats; blank values are unavailable."]
    for path in files:
        chunks.extend(["BEGIN CSV " + path.stem, path.read_text(encoding="utf-8-sig").rstrip(), "END CSV " + path.stem])
    return "\n\n".join(chunks) + "\n"


def source_data(source, destination):
    entries = {}
    for number in range(1, 7):
        files = sorted((source / "source_data").glob(f"fig{number}_*.csv"))
        assert files
        descriptions = {
            1: "Panel a is a model diagram with users 1 and 2 on tone 1 and users 3 and 4 on tone 2. Panels b and c use the gap ledger.",
            2: "Panels a and b show exact rational channel coordinates, c their pairwise overlaps, d the price relaxation and e and f the 512-instance table comparison.",
            3: "Panels a and b are geometric illustrations in arbitrary units. Panel c gives Gaussian expectations. Panels d to f use the simulated gap, retention and coverage data."}
        entries[f"Figure_{number}.txt"] = annotated(f"Figure_{number}", descriptions.get(number, "Main-article figure panels, identified by each source-table name."), files)
    for name, (description, stems) in SUPPLEMENTARY_DATA.items():
        files = [source / "supplementary" / "data" / (stem + ".csv") for stem in stems]
        entries[name + ".txt"] = annotated(name, description, files)
    assert len(entries) == 30
    fixtures = sorted((source / "supplementary" / "data").glob("proof_*.csv"))
    if fixtures:
        entries["mathematical_fixtures.txt"] = annotated("Mathematical_fixtures", "Exact rational counterexamples accompanying Supplementary Note 2. Fractions retain their integer numerator and denominator.", fixtures)
    entries["README.txt"] = "Source Data for Bounding the rate loss of individual paired wireless uplink schedules.\nSix main figures, eight supplementary figures and sixteen supplementary tables each have one annotated UTF-8 text file containing labelled CSV blocks. Source filenames, denominators and timing cohorts are retained. Scientific explanations and aggregation rules are in the corresponding legends and Supplementary Notes. Raw and reconstructed measurement channels are excluded.\n"
    entries["input_sha256.txt"] = (source / "source_data" / "input_sha256.txt").read_text()
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "Source_Data.zip"
    matches = False
    if path.exists():
        with zipfile.ZipFile(path) as archive:
            matches = archive.namelist() == list(entries) and all(
                archive.read(name) == text.encode("utf-8") for name, text in entries.items()
            )
    if not matches:
        with tempfile.TemporaryDirectory(dir=destination) as scratch:
            replacement = Path(scratch) / path.name
            with zipfile.ZipFile(replacement, "w") as archive:
                for name, text in entries.items():
                    archive.writestr(zipfile.ZipInfo(name), text.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
            replacement.replace(path)
    path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n", encoding="ascii")


def main():
    destination = Path(__file__).resolve().parents[2] / "supplementary_materials"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=destination / "reproduction" / "Gate_4")
    parser.add_argument("--tectonic")
    parser.add_argument("--only-cached", action="store_true", help="Compile without fetching any TeX resources.")
    args = parser.parse_args()
    text = expand(args.source / "Supplementary_Information.tex")
    text = re.sub(r"(?:supplementary/)?figures/(sfig[1-8]\.pdf)", r"Supplementary_Figures/\1", text)
    assert r"\input{" not in text
    assert len(re.findall(r"\\section\{", text)) == 7
    assert len(re.findall(r"\\bibitem\{", text)) == 51
    all_labels = re.findall(r'\\label\{([^}]+)\}', text)
    assert len(all_labels)==len(set(all_labels)), 'Duplicate supplement labels'
    labels = ["comparison", *["table" + str(n) for n in range(1,11)], "rates", "compute", "decomposition", "refinement", "hardware_calibration"]
    assert len(labels)==16 and all(text.count(r"\label{supp:"+label+"}")==1 for label in labels)
    assert all(text.count(r"\label{supp:fig" + str(number) + "}") == 1 for number in range(1, 9))
    (destination / "Supplementary_Information.tex").write_text(text, encoding="utf-8")
    figures = destination / "Supplementary_Figures"
    figures.mkdir(exist_ok=True)
    for number in range(1, 9):
        filename = f"sfig{number}.pdf"
        shutil.copy2(args.source / "supplementary" / "figures" / filename, figures / filename)
    source_data(args.source, destination.parent / "data")
    if args.tectonic:
        subprocess.run([args.tectonic, *(["--only-cached"] if args.only_cached else []), "--keep-logs", "Supplementary_Information.tex"], cwd=destination, check=True)
    print("Assembled seven supplementary notes, eight figure assets and 30 source-data files.")


if __name__ == "__main__":
    main()
