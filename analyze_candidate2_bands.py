"""Read-only candidate2 spectral contrast; saves small derived reports, never fits a model."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np


TAKES = {
    'quiet': '8f3e07abc7344ab89b95827e99b1da16',
    'normal': 'e3d4b5c09a1e4c368772db52df67e224',
    'light': '4640f7e3c8e24aca9c2299d0680a996d',
    'knock': '8567d49fc8bf4b8d97cdead6fc6b20c3',
}
BANDS = [(0, 1000), (1000, 4000), (4000, 8000), (8000, 16000), (16000, 24000)]


def analyze(source, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    frequency = np.arange(1, 1201) * 20.0  # DC dropped: saved index 0 is 20 Hz.
    weight = np.logspace(0, np.log2(np.log2(24000)), 1200, base=2)
    sided = np.ones(1200)
    sided[-1] = .5  # Nyquist has no negative-frequency partner.
    power, levels = {}, {}
    for condition, ident in TAKES.items():
        path = Path(source) / ('take_' + ident + '.npz')
        with np.load(path, allow_pickle=False) as data:
            config = json.loads(str(data['config_json']))
            info = json.loads(str(data['metadata_json']))
            assert config['setup_id'] == 'A_wood30x30x6_v3_candidate2'
            assert info['recording_kind'] == 'diagnostic' and info['valid']
            assert config['sample_rate'] == 48000 and config['fft_window_samples'] == 2400
            power[condition] = (data['X'].astype(float) / weight) ** 2 * sided
            levels[condition] = dict(take_id=info['take_id'], windows=len(data['X']),
                median_rms_pct=float(np.median(data['rms_fs']) * 100),
                p10_rms_pct=float(np.percentile(data['rms_fs'], 10) * 100),
                p95_rms_pct=float(np.percentile(data['rms_fs'], 95) * 100),
                p95_peak_pct=float(np.percentile(data['peak_fs'], 95) * 100),
                max_peak_pct=float(data['peak_fs'].max() * 100))
    rows, summaries = [], []
    quiet_total = power['quiet'].sum(axis=1).mean()
    for lo, hi in BANDS:
        mask = (frequency >= lo) & ((frequency <= hi) if hi == 24000 else (frequency < hi))
        energy = {k: v[:, mask].sum(axis=1) for k, v in power.items()}
        qmedian = float(np.median(energy['quiet']))
        qp95 = float(np.percentile(energy['quiet'], 95))
        share = float(energy['quiet'].mean() / quiet_total)
        for condition, values in energy.items():
            summaries.append(dict(band_hz=[lo, hi], condition=condition,
                median_proxy_energy=float(np.median(values)),
                p10_proxy_energy=float(np.percentile(values, 10)),
                p95_proxy_energy=float(np.percentile(values, 95)),
                max_proxy_energy=float(values.max())))
        for condition in ('normal', 'light'):
            median = float(np.median(energy[condition]))
            p10 = float(np.percentile(energy[condition], 10))
            rows.append(dict(low_hz=lo, high_hz=hi, condition=condition,
                quiet_mean_energy_share=share,
                median_contrast_db=float(10 * np.log10(median / qmedian)),
                p10_contrast_db=float(10 * np.log10(p10 / qmedian)),
                fraction_above_quiet_p95=float(np.mean(energy[condition] > qp95)),
                p10_over_quiet_p95_db=float(10 * np.log10(p10 / qp95))))
    mean_quiet = power['quiet'].mean(axis=0)
    top = np.argsort(mean_quiet)[-12:][::-1]
    report = dict(source=str(source), levels=levels, band_contrasts=rows,
        all_condition_band_energy=summaries,
        top_quiet_bins=[dict(hz=float(frequency[i]), share=float(mean_quiet[i] / mean_quiet.sum())) for i in top],
        headroom_db_to_70pct=float(20 * np.log10(70 / levels['knock']['max_peak_pct'])),
        headroom_db_to_44_3pct=float(20 * np.log10(44.3 / levels['knock']['max_peak_pct'])),
        method='Undo saved pink weighting; sum squared temporally smoothed Hamming FFT magnitudes; half Nyquist. DC omitted. Energy units are relative; common scale cancels in contrasts. Correct frequency axis starts at 20 Hz. This cannot reconstruct unsmoothed PCM power or establish noise gain dependence.',
        revised_rule='For a fixed listed band: light P10 > quiet P95 and >=90% light windows above quiet P95; normal >=90% above quiet P95; knock peak <70% FS. These are exploratory acceptance diagnostics, not a final performance test.',
        joint_grid_search_run=False, model_fitted=False, new_capture_started=False)
    report['passing_bands'] = [r['low_hz'] for r in rows if r['condition'] == 'light'
        and r['p10_over_quiet_p95_db'] > 0 and r['fraction_above_quiet_p95'] >= .9
        and next(n for n in rows if n['low_hz'] == r['low_hz'] and n['condition'] == 'normal')['fraction_above_quiet_p95'] >= .9
        and levels['knock']['max_peak_pct'] < 70]
    (output / 'band_analysis.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    with (output / 'band_contrasts.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='data_sessions/diagnostics/final_v3_acceptance/20261019_125214_3db18f7f')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    analyze(args.source, args.output)
