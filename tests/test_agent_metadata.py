from pathlib import Path
import yaml


def test_openai_agent_metadata_is_utf8_and_readable() -> None:
    data = yaml.safe_load(Path('agents/openai.yaml').read_text(encoding='utf-8'))
    interface = data['interface']
    assert interface['display_name'] == 'Impl Phase Coach'
    assert '实现阶段' in interface['short_description']
    assert '$impl-phase-coach' in interface['default_prompt']
    assert '阶段目标' in interface['default_prompt']
