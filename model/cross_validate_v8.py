"""Leakage-safe grouped development experiment for v8 dead-ball evidence."""
import argparse
import json
from pathlib import Path
import statistics
import time

import numpy as np

from evaluation import possession_metrics as pm
from model.external_idsse import SOURCE_REVISION, digest, load_match
from model.inference import infer
from model.stoppage import add_stoppage_evidence
from model.temporal import load_config
from model.tune_skillcorner import assign_candidates
from model.tune_stoppage import official_score


def validate_manifest(manifest):
    sources = manifest.get('sources', {})
    idsse = sources.get('idsse', {})
    if idsse.get('role') != 'development_cross_validation':
        raise ValueError('IDSSE must be the explicit development source')
    development = [row['id'] for row in idsse.get('matches', [])]
    if not development or len(development) != len(set(development)):
        raise ValueError('development match IDs must be nonempty and unique')
    final = set(manifest.get('untouched_final_test', []))
    if final & set(development):
        raise ValueError('final-test/development overlap')
    for source in ('wcsf', 'challenge_public'):
        if 'excluded' not in sources.get(source, {}).get('role', ''):
            raise ValueError('{} must remain excluded'.format(source))
    return development


def leave_one_match_out(match_ids):
    if len(match_ids) < 2 or len(match_ids) != len(set(match_ids)):
        raise ValueError('need at least two unique match groups')
    return [{'test': heldout, 'train': [match for match in match_ids if match != heldout]}
            for heldout in match_ids]


def merge_official_scores(scores):
    if not scores:
        raise ValueError('cannot merge empty scores')
    confusion = np.sum([np.asarray(score['confusion'], dtype=np.int64)
                        for score in scores], axis=0)
    cm3 = pm.scored_confusion(confusion)
    strict, both_alive = pm.team_accuracy(cm3)
    spell_rows = {}
    spell_f1s = []
    for threshold in pm.SPELL_IOUS:
        parts = [score['spell_f1'][threshold] for score in scores]
        matched = sum(row['n_matched'] for row in parts)
        spurious = sum(row['n_spurious'] for row in parts)
        missed = sum(row['n_missed'] for row in parts)
        precision = matched / (matched + spurious) if matched + spurious else 0.0
        recall = matched / (matched + missed) if matched + missed else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        spell_rows[threshold] = {'precision': precision, 'recall': recall, 'f1': f1,
                                 'n_matched': matched, 'n_spurious': spurious,
                                 'n_missed': missed}
        spell_f1s.append(f1)
    per_class = {}
    for index, label in enumerate(pm.SCORED):
        precision, recall, f1 = pm.per_class_prf(cm3, index)
        per_class[label] = {'precision': precision, 'recall': recall, 'f1': f1,
                            'support': int(cm3[index].sum())}
    n_gt_segments = sum(score['n_gt_segments'] for score in scores)
    n_pred_segments = sum(score['n_pred_segments'] for score in scores)
    return {
        'accuracy': pm.accuracy(cm3),
        'macro_f1': pm.macro_f1(cm3),
        'spell_f1_mean': float(np.mean(spell_f1s)),
        'spell_f1_at_headline': spell_rows[pm.SPELL_IOU_HEADLINE]['f1'],
        'spell_f1': spell_rows,
        'alive_dead_f1': pm.alive_dead_f1(cm3),
        'team_acc_gt_alive': strict,
        'team_acc_both_alive': both_alive,
        'n_gt_spells': sum(score['n_gt_spells'] for score in scores),
        'n_pred_spells': sum(score['n_pred_spells'] for score in scores),
        'n_gt_segments': n_gt_segments,
        'n_pred_segments': n_pred_segments,
        'fragmentation': n_pred_segments / n_gt_segments if n_gt_segments else 0.0,
        'n_graded': int(cm3.sum()),
        'n_abstain_on_graded': int(cm3[:, pm.X].sum()),
        'confusion': confusion.tolist(),
        'per_class': per_class,
    }


def select_candidate(rows, baseline_name, minimum_accuracy_delta,
                     minimum_both_live_delta):
    by_name = {row['name']: row for row in rows}
    if baseline_name not in by_name or len(by_name) != len(rows):
        raise ValueError('missing baseline or duplicate candidate name')
    baseline = by_name[baseline_name]['metrics']
    eligible = [row for row in rows
                if row['metrics']['accuracy'] >= baseline['accuracy'] + minimum_accuracy_delta
                and row['metrics']['team_acc_both_alive'] >=
                baseline['team_acc_both_alive'] + minimum_both_live_delta]
    return max(eligible, key=lambda row: (row['metrics']['spell_f1_mean'],
                                          row['metrics']['macro_f1'],
                                          row['metrics']['accuracy']))


def _summary(score):
    keys = ('accuracy', 'macro_f1', 'spell_f1_mean', 'spell_f1_at_headline',
            'alive_dead_f1', 'team_acc_gt_alive', 'team_acc_both_alive',
            'n_gt_spells', 'n_pred_spells', 'fragmentation', 'n_graded',
            'n_abstain_on_graded')
    return {**{key: score[key] for key in keys},
            'per_class': score['per_class'], 'confusion': score['confusion']}


def _boundary_metrics(labels, reference, blocks):
    onset, release, missed = [], [], 0
    for _, first, last in blocks:
        frame = first
        while frame <= last:
            if reference[frame] != 'D':
                frame += 1
                continue
            start = frame
            while frame <= last and reference[frame] == 'D':
                frame += 1
            stop = frame
            hits = [index for index in range(start, stop) if labels[index] == 'D']
            if not hits:
                missed += 1
                continue
            first_hit, last_hit = hits[0], hits[-1]
            predicted_stop = last_hit + 1
            while predicted_stop <= last and labels[predicted_stop] == 'D':
                predicted_stop += 1
            onset.append(first_hit - start)
            release.append(predicted_stop - stop)

    def stats(values):
        if not values:
            return {'count': 0, 'median_frames': None, 'mean_frames': None,
                    'p90_abs_frames': None}
        return {'count': len(values), 'median_frames': statistics.median(values),
                'mean_frames': sum(values) / len(values),
                'p90_abs_frames': sorted(abs(value) for value in values)[
                    int(.9 * (len(values) - 1))]}
    return {'onset': stats(onset), 'release': stats(release),
            'missed_dead_segments': missed}


def _live_dead_confusion(confusion):
    cm = np.asarray(confusion, dtype=np.int64)
    return {'rows': ['ground_truth_live', 'ground_truth_dead'],
            'columns': ['predicted_live', 'predicted_dead', 'predicted_X'],
            'counts': [[int(cm[:2, :2].sum()), int(cm[:2, 2].sum()), int(cm[:2, 3].sum())],
                       [int(cm[2, :2].sum()), int(cm[2, 2]), int(cm[2, 3])]]}


def _evaluate(match, config):
    assign_candidates(match['evidence'], config['control_distance_m'],
                      config['opponent_margin_m'])
    add_stoppage_evidence(match['evidence'], match['blocks'], config, (105.0, 68.0))
    started = time.perf_counter()
    labels, reasons = infer(match['evidence'], match['blocks'], config)
    elapsed = time.perf_counter() - started
    score = official_score(labels, match['reference'], match['blocks'])
    return {'score': score, 'labels': labels, 'reasons': reasons,
            'runtime_seconds': elapsed,
            'boundary': _boundary_metrics(labels, match['reference'], match['blocks'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--manifest', default=Path('model/dataset_manifest_v8.json'), type=Path)
    parser.add_argument('--protocol', default=Path('model/v8_protocol.json'), type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--config-out', required=True, type=Path)
    args = parser.parse_args()
    if len({path.resolve() for path in (args.manifest, args.protocol, args.output,
                                       args.config_out)}) != 4:
        parser.error('inputs and outputs must be distinct')
    manifest = json.loads(args.manifest.read_text())
    protocol = json.loads(args.protocol.read_text())
    if digest(args.manifest) != protocol['manifest_sha256']:
        raise ValueError('dataset manifest hash mismatch')
    if digest(protocol['base_config']) != protocol['base_config_sha256']:
        raise ValueError('base config hash mismatch')
    match_ids = validate_manifest(manifest)
    if manifest['sources']['idsse']['source_revision'] != SOURCE_REVISION:
        raise ValueError('IDSSE source revision mismatch')
    base = load_config(protocol['base_config'])
    candidates = [(row['name'], dict(base, **row['overrides']))
                  for row in protocol['candidates']]
    if candidates[0][0] != 'v7_baseline' or candidates[0][1] != base:
        raise ValueError('first candidate must reproduce v7 exactly')

    matches = {}
    inputs = []
    load_started = time.perf_counter()
    for match_id in match_ids:
        match = load_match(args.data_root / (match_id + '.metadata.xml'),
                           args.data_root / (match_id + '.tracking.xml'), base)
        if match['id'] != 'DFL-MAT-' + match_id:
            raise ValueError('requested match ID mismatch')
        matches[match_id] = match
        inputs.append({key: match[key] for key in ('id', 'home', 'away', 'date', 'audit')})
        print('loaded', match_id, flush=True)
    load_seconds = time.perf_counter() - load_started

    raw = {}
    candidate_rows = []
    for name, config in candidates:
        raw[name] = {}
        per_match = []
        for match_id in match_ids:
            result = _evaluate(matches[match_id], config)
            raw[name][match_id] = result
            summary = _summary(result['score'])
            summary.update(id=match_id, runtime_seconds=result['runtime_seconds'],
                           boundary=result['boundary'])
            per_match.append(summary)
        aggregate = merge_official_scores([raw[name][match_id]['score'] for match_id in match_ids])
        candidate_rows.append({'name': name, 'metrics': _summary(aggregate),
                               'macro_match_accuracy': statistics.mean(
                                   row['accuracy'] for row in per_match),
                               'runtime_seconds': sum(row['runtime_seconds'] for row in per_match),
                               'per_match': per_match})
        print('evaluated', name, aggregate['spell_f1_mean'], aggregate['accuracy'], flush=True)

    settings = protocol['selection']
    folds = []
    oof_scores = []
    for fold in leave_one_match_out(match_ids):
        training_rows = []
        for name, _ in candidates:
            merged = merge_official_scores([raw[name][match_id]['score']
                                             for match_id in fold['train']])
            training_rows.append({'name': name, 'metrics': merged})
        selected = select_candidate(
            training_rows, 'v7_baseline',
            settings['minimum_accuracy_delta_vs_v7'],
            settings['minimum_both_live_team_accuracy_delta_vs_v7'])
        test_result = raw[selected['name']][fold['test']]
        oof_scores.append(test_result['score'])
        folds.append({**fold, 'selected': selected['name'],
                      'training_metrics': _summary(selected['metrics']),
                      'test_metrics': _summary(test_result['score'])})
    oof = merge_official_scores(oof_scores)

    final_rows = [{'name': row['name'], 'metrics': row['metrics']} for row in candidate_rows]
    selected = select_candidate(final_rows, 'v7_baseline',
                                settings['minimum_accuracy_delta_vs_v7'],
                                settings['minimum_both_live_team_accuracy_delta_vs_v7'])
    selected_spec = next(row for row in protocol['candidates'] if row['name'] == selected['name'])
    frozen = dict(base, **selected_spec['overrides'], version=8)
    args.config_out.parent.mkdir(parents=True, exist_ok=True)
    args.config_out.write_text(json.dumps(frozen, indent=2) + '\n')

    selected_raw = raw[selected['name']]
    payload = {
        'task': 'TASK-015', 'created': '2026-11-12',
        'code_revision_before_task': protocol['code_revision_before_task'],
        'manifest_sha256': digest(args.manifest), 'protocol_sha256': digest(args.protocol),
        'base_config_sha256': digest(protocol['base_config']),
        'selected_config_sha256': digest(args.config_out),
        'seed': None, 'deterministic': True, 'load_runtime_seconds': load_seconds,
        'inputs': inputs, 'candidates': candidate_rows, 'outer_folds': folds,
        'oof_selection_metrics': _summary(oof),
        'selected': selected['name'], 'selected_metrics': _summary(selected['metrics']),
        'selected_live_dead_confusion': _live_dead_confusion(selected['metrics']['confusion']),
        'selected_boundary_by_match': {
            match_id: selected_raw[match_id]['boundary'] for match_id in match_ids},
        'final_test': {'status': 'not_run', 'reason': 'no untouched matches available'},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    print('OOF selected spellF1', oof['spell_f1_mean'], 'accuracy', oof['accuracy'])
    print('frozen', selected['name'], 'spellF1', selected['metrics']['spell_f1_mean'],
          'accuracy', selected['metrics']['accuracy'])


if __name__ == '__main__':
    main()
