"""Development-only search for the observed unattended-ball stoppage cue.

The official metric implementation is imported unchanged. Reference labels are
used only here for external development scoring and never enter model evidence.
"""
import argparse
from collections import Counter
from itertools import product
import json
from pathlib import Path

from evaluation import possession_metrics as pm
from model.external_idsse import digest, load_match
from model.inference import infer
from model.stoppage import add_stoppage_evidence
from model.temporal import load_config


def official_score(labels, reference, blocks):
    """Score labels while inserting an ungraded separator at each half boundary."""
    if len(labels) != len(reference):
        raise ValueError('prediction/reference length mismatch')
    truth, prediction = [], []
    for _, first, last in blocks:
        if first < 0 or last < first or last >= len(labels):
            raise ValueError('invalid half boundary')
        truth.extend(value if value in ('H', 'A', 'D') else 'X'
                     for value in reference[first:last + 1])
        prediction.extend(labels[first:last + 1])
        truth.append('X')
        prediction.append('X')
    return pm.evaluate(pm.label_codes(truth), pm.label_codes(prediction))


def select_best(candidates):
    """Apply the challenge ranking order, with accuracy only as a final tie-break."""
    if not candidates:
        raise ValueError('empty search')
    return max(candidates, key=lambda row: (
        row['metrics']['spell_f1_mean'],
        row['metrics']['macro_f1'],
        row['metrics']['accuracy'],
    ))


def _candidate_metrics(matches, config, pitch):
    truth, prediction = [], []
    dead_total = dead_correct = live_total = live_correct = 0
    label_counts = Counter()
    for match in matches:
        add_stoppage_evidence(match['evidence'], match['blocks'], config, pitch)
        labels, _ = infer(match['evidence'], match['blocks'], config)
        label_counts.update(labels)
        for _, first, last in match['blocks']:
            refs = match['reference'][first:last + 1]
            preds = labels[first:last + 1]
            truth.extend(value if value in ('H', 'A', 'D') else 'X' for value in refs)
            prediction.extend(preds)
            truth.append('X')
            prediction.append('X')
        for target, label in zip(match['reference'], labels):
            if target == 'D':
                dead_total += 1
                dead_correct += label == 'D'
            elif target in ('H', 'A'):
                live_total += 1
                live_correct += label == target
    metrics = pm.evaluate(pm.label_codes(truth), pm.label_codes(prediction))
    keep = ('spell_f1_mean', 'spell_f1_at_headline', 'macro_f1', 'accuracy',
            'alive_dead_f1', 'team_acc_gt_alive', 'team_acc_both_alive',
            'n_gt_spells', 'n_pred_spells', 'spell_count_error', 'fragmentation',
            'n_graded', 'n_abstain_on_graded')
    summary = {name: metrics[name] for name in keep}
    summary.update(dead_recall=dead_correct / dead_total if dead_total else None,
                   live_team_agreement=live_correct / live_total if live_total else None,
                   label_counts=dict(label_counts))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--protocol', default=Path('model/stoppage_search.json'), type=Path)
    parser.add_argument('--base-config', default=Path('model/config_v4.json'), type=Path)
    parser.add_argument('--config-out', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.config_out.resolve() in (args.protocol.resolve(), args.base_config.resolve()) or \
            args.output.resolve() in (args.protocol.resolve(), args.base_config.resolve(),
                                      args.config_out.resolve()):
        parser.error('input and output paths must be distinct')

    protocol = json.loads(args.protocol.read_text())
    base = load_config(args.base_config)
    matches = []
    for match_id in protocol['development']:
        match = load_match(args.data_root / (match_id + '.metadata.xml'),
                           args.data_root / (match_id + '.tracking.xml'), base)
        if match['id'] != 'DFL-MAT-' + match_id:
            raise ValueError('requested match ID mismatch')
        matches.append(match)
        print('development loaded', match_id, flush=True)

    keys = list(protocol['grid'])
    candidates = []
    for values in product(*(protocol['grid'][key] for key in keys)):
        config = dict(base, **dict(zip(keys, values)))
        metrics = _candidate_metrics(matches, config, tuple(protocol['pitch_m']))
        candidates.append({'parameters': dict(zip(keys, values)), 'metrics': metrics})
        print('candidate', dict(zip(keys, values)), metrics['spell_f1_mean'], flush=True)
    selected = select_best(candidates)
    config = dict(base, **selected['parameters'], version=7)
    args.config_out.parent.mkdir(parents=True, exist_ok=True)
    args.config_out.write_text(json.dumps(config, indent=2) + '\n')
    payload = {
        'source': protocol['source'],
        'source_revision': protocol['source_revision'],
        'development': protocol['development'],
        'selection': protocol['selection'],
        'protocol_sha256': digest(args.protocol),
        'base_config_sha256': digest(args.base_config),
        'selected_config_sha256': digest(args.config_out),
        'selected': selected,
        'candidates': candidates,
        'matches': [{key: match[key] for key in ('id', 'home', 'away', 'date', 'audit')}
                    for match in matches],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    print('selected', selected['parameters'], selected['metrics']['spell_f1_mean'])


if __name__ == '__main__':
    main()
