"""Separate development search and frozen holdout evaluation on IDSSE matches.

Run with --stage tune first, then --stage evaluate with the generated config.
No challenge labels or prior SkillCorner holdouts are read.
"""
import argparse
from collections import Counter
from itertools import product
import json
from pathlib import Path

from model.external_idsse import load_match, score_labels, merge_scores, digest, SOURCE_REVISION
from model.inference import infer
from model.temporal import load_config
from model.tune_skillcorner import assign_candidates


def validate_protocol(protocol):
    dev, test = protocol['development'], protocol['holdout']
    if (not dev or not test or len(set(dev)) != len(dev) or len(set(test)) != len(test)
            or set(dev) & set(test)):
        raise ValueError('development and holdout must be nonempty, unique, disjoint matches')


def select_best(candidates):
    if not candidates:
        raise ValueError('empty search')
    return max(candidates, key=lambda row: (row['aggregate']['accuracy'], row['aggregate']['macro_f1']))


def evaluate(match, config):
    assign_candidates(match['evidence'], config['control_distance_m'], config['opponent_margin_m'])
    labels, _ = infer(match['evidence'], match['blocks'], config)
    transitions = sum(labels[i] != labels[i-1] for _, start, end in match['blocks']
                      for i in range(start+1, end+1))
    durations = []
    for _, start, end in match['blocks']:
        run = 1
        for frame in range(start+1, end+1):
            if labels[frame] == labels[frame-1]:
                run += 1
            else:
                durations.append(run); run = 1
        durations.append(run)
    return {'score': score_labels(labels, match['reference']), 'labels': dict(Counter(labels)),
            'transitions': transitions, 'intervals': len(durations),
            'min_interval_frames': min(durations), 'max_interval_frames': max(durations),
            'mean_interval_seconds': sum(durations)/len(durations)/25}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['tune', 'evaluate'], required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, default=Path('model/idsse_protocol.json'))
    parser.add_argument('--base-config', type=Path, default=Path('model/config_v4.json'))
    parser.add_argument('--config', type=Path, help='frozen candidate for evaluate')
    parser.add_argument('--config-out', type=Path, help='candidate written by tune')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if (args.stage == 'tune' and not args.config_out) or (args.stage == 'evaluate' and not args.config):
        parser.error('tune needs --config-out; evaluate needs --config')
    outputs = [args.output] + ([args.config_out] if args.stage == 'tune' else [])
    protected = [args.base_config, args.protocol] + ([args.config] if args.config else [])
    if len({p.resolve() for p in outputs + protected}) != len(outputs + protected):
        parser.error('input and output paths must be distinct')
    protocol = json.loads(args.protocol.read_text())
    validate_protocol(protocol)
    if protocol['source_revision'] != SOURCE_REVISION:
        raise ValueError('unexpected source revision')
    base = load_config(args.base_config)
    payload = {'source': 'IDSSE / DFL / Sportec, PySport mirror', 'source_revision': SOURCE_REVISION,
               'protocol_sha256': digest(args.protocol), 'base_config_sha256': digest(args.base_config),
               'stage': args.stage, 'matches': [],
               'implementation_sha256': {str(p): digest(p) for p in map(Path,
                   ['model/external_idsse.py', 'model/tune_idsse.py', 'model/inference.py',
                    'model/temporal.py', 'model/tune_skillcorner.py'])}}
    if args.stage == 'tune':
        keys = list(protocol['grid'])
        configs = [dict(base, **dict(zip(keys, values)))
                   for values in product(*(protocol['grid'][k] for k in keys))]
        if base not in configs:
            configs.append(base)
        candidates = [{'config': config, 'scores': []} for config in configs]
        for match_id in protocol['development']:
            match = load_match(args.data_root / (match_id+'.metadata.xml'),
                               args.data_root / (match_id+'.tracking.xml'), base)
            if match['id'] != 'DFL-MAT-'+match_id:
                raise ValueError('requested match ID mismatch')
            payload['matches'].append({k: match[k] for k in ('id', 'home', 'away', 'date', 'audit')})
            for candidate in candidates:
                candidate['scores'].append(evaluate(match, candidate['config'])['score'])
            print('development processed', match_id, flush=True)
        for candidate in candidates:
            candidate['aggregate'] = merge_scores(candidate['scores'])
        selected = select_best(candidates)
        config = dict(selected['config'], version=5)
        args.config_out.parent.mkdir(parents=True, exist_ok=True)
        args.config_out.write_text(json.dumps(config, indent=2)+'\n')
        payload.update(candidates=candidates, selected_config=config,
                       selected_aggregate=selected['aggregate'], config_sha256=digest(args.config_out))
        print('selected development accuracy', selected['aggregate']['accuracy'], flush=True)
    else:
        config = load_config(args.config)
        payload['config_sha256'] = digest(args.config)
        for match_id in protocol['holdout']:
            match = load_match(args.data_root / (match_id+'.metadata.xml'),
                               args.data_root / (match_id+'.tracking.xml'), base)
            if match['id'] != 'DFL-MAT-'+match_id:
                raise ValueError('requested match ID mismatch')
            result = {k: match[k] for k in ('id', 'home', 'away', 'date', 'audit')}
            result.update(baseline=evaluate(match, base), candidate=evaluate(match, config))
            payload['matches'].append(result)
            print('holdout processed', match_id, flush=True)
        for name in ('baseline', 'candidate'):
            payload[name] = merge_scores([m[name]['score'] for m in payload['matches']])
        print('holdout accuracy', payload['candidate']['accuracy'], flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True)+'\n')


if __name__ == '__main__':
    main()
