"""One-shot comparison on the reserved WCSF professional match."""
import argparse
from collections import Counter
import json
from pathlib import Path

from model.external_idsse import digest
from model.external_skillcorner import scale_config
from model.external_wcsf import FPS, PITCH_M, load_match
from model.inference import infer
from model.stoppage import add_stoppage_evidence
from model.temporal import load_config
from model.tune_skillcorner import assign_candidates
from model.tune_stoppage import official_score


def evaluate_models(match, candidates):
    results = {}
    for name, source_config in candidates:
        config = scale_config(source_config, FPS)
        assign_candidates(match['evidence'], config['control_distance_m'],
                          config['opponent_margin_m'])
        add_stoppage_evidence(match['evidence'], match['blocks'], config, PITCH_M)
        labels, _ = infer(match['evidence'], match['blocks'], config)
        complete = official_score(labels, match['reference'], match['blocks'])
        keep = ('spell_f1_mean', 'spell_f1_at_headline', 'macro_f1', 'accuracy',
                'alive_dead_f1', 'team_acc_gt_alive', 'team_acc_both_alive',
                'n_gt_spells', 'n_pred_spells', 'spell_count_error',
                'fragmentation', 'n_graded', 'n_abstain_on_graded')
        results[name] = {key: complete[key] for key in keep}
        results[name].update(per_class=complete['per_class'],
                             confusion=complete['confusion'],
                             label_counts=dict(Counter(labels)))
    return results


def select_final(results):
    if not results:
        raise ValueError('empty comparison')
    return max(results, key=lambda name: (
        results[name]['spell_f1_mean'],
        results[name]['macro_f1'],
        results[name]['accuracy'],
    ))


def reserved_paths(protocol, data_root):
    match = protocol['matches'][0]
    paths = [data_root / name for name in match['files']]
    for path in paths:
        if digest(path) != match['input_sha256'].get(path.name):
            raise ValueError('archive hash mismatch: {}'.format(path))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', default=Path('model/wcsf_protocol.json'), type=Path)
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('one-shot output already exists; refusing to overwrite it')
    protocol = json.loads(args.protocol.read_text())
    candidate_specs = protocol['one_shot_comparison']
    candidates = []
    for spec in candidate_specs:
        path = Path(spec['path'])
        if digest(path) != spec['sha256']:
            raise ValueError('candidate hash mismatch: {}'.format(path))
        candidates.append((spec['name'], load_config(path)))
    paths = reserved_paths(protocol, args.data_root)
    match = load_match(paths, candidates[0][1])
    if match['id'] != protocol['matches'][0]['id']:
        raise ValueError('reserved match ID mismatch')
    results = evaluate_models(match, candidates)
    selected = select_final(results)
    payload = {
        'source': protocol['source'],
        'source_revision': protocol['source_revision'],
        'protocol_sha256': digest(args.protocol),
        'match': {'id': match['id'], 'description': protocol['matches'][0]['description'],
                  'audit': match['audit']},
        'selection': protocol['selection_policy'],
        'results': results,
        'selected': selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    print('frames', match['audit']['frames'])
    for name, metrics in results.items():
        print(name, 'spellF1', metrics['spell_f1_mean'], 'accuracy', metrics['accuracy'])
    print('selected', selected)
    print('output', args.output)


if __name__ == '__main__':
    main()
