"""The default profiles return an edited Approved term to review."""
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


class ApprovalResetDefault(unittest.TestCase):
  def test_profiles_enable_reset(self):
    for rel in ('skills/damapl-business-glossary/assets/profiles/minimal.yaml',
                'examples/data/glossary/rules/profile.yaml'):
      prof = yaml.safe_load((ROOT / rel).read_text(encoding='utf-8'))
      self.assertIs(prof.get('approval_reset'), True, rel)


if __name__ == '__main__':
  unittest.main()
