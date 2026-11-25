"""Score human-matched events; never infer errors from the final total alone."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean


def evaluate(session, rows):
    auto = {str(e['id']): e for e in session['events'] if e['type'] == 'auto_count'}
    if len(auto) != session['automatic_count']:
        raise ValueError('日志自动计数与自动事件数量不一致')
    matched, actions, delays = set(), set(), []
    missed = 0
    for row in rows:
        action = row['action_id'].strip()
        if not action or action in actions:
            raise ValueError('每个真实动作必须有独立且非空的 action_id')
        actions.add(action)
        event = row['matched_auto_event_id'].strip()
        if not event:
            missed += 1
            continue
        if event not in auto or event in matched:
            raise ValueError('对应的自动事件不存在或被重复匹配')
        matched.add(event)
        source, display = row['action_time_ms'].strip(), row['display_time_ms'].strip()
        if bool(source) != bool(display):
            raise ValueError('延迟测量需同时填写动作时刻和界面显示时刻；未测量时两项都留空')
        if source:
            delay = float(display) - float(source)
            if delay < 0:
                raise ValueError('界面早于真实动作；请复查是否误计或时间轴未对齐')
            delays.append(delay)
    return {
        '真实动作次数': len(actions), '原始自动计数': len(auto),
        '正确对应次数': len(matched), '误计次数': len(auto) - len(matched), '漏计次数': missed,
        '手动调整次数净值': session['manual_adjustment'], '修正后总数': session['final_count'],
        '已测反馈延迟数量': len(delays), '反馈延迟均值_ms': mean(delays) if delays else None,
        '反馈延迟最大值_ms': max(delays) if delays else None,
    }


def main():
    parser = argparse.ArgumentParser(description='用人工逐次标注核对自动计数')
    parser.add_argument('session', type=Path, help='页面导出的计数记录 JSON')
    parser.add_argument('annotations', type=Path, help='人工标注 CSV；每个真实动作一行')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.annotations.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    result = evaluate(json.loads(args.session.read_text('utf-8')), rows)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
