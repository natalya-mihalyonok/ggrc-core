# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test import of Audit and mapped objects."""

from collections import OrderedDict

from ggrc.models import all_models

from integration.ggrc import TestCase
from integration.ggrc.models import factories
from ggrc.converters import errors

class TestAuditImport(TestCase):
  """Audit import test class."""

  def setUp(self):
    """Set up for Audit test cases."""
    super(TestAuditImport, self).setUp()
    self.client.get("/login")

  def test_audit_import_db_lock(self):
    """Import 2 audits one of them with control"""
    with factories.single_commit():
      program = factories.ProgramFactory()
      control = factories.ControlFactory()
      factories.RelationshipFactory(source=program, destination=control)

    response = self.import_data(*[
        OrderedDict([
            ("object_type", "Audit"),
            ("Code", ""),
            ("Title", "Audit-import-2"),
            ("State", "In Progress"),
            ("Audit Captains", "user@example.com"),
            ("Program", program.slug),
            ("map:control versions", ""),
        ]),
        OrderedDict([
            ("object_type", "Audit"),
            ("Code", ""),
            ("Title", "Audit-import-3"),
            ("State", "Planned"),
            ("Audit Captains", "user@example.com"),
            ("Program", program.slug),
            ("map:control versions", control.slug),
        ])
    ])
    self.assertEquals(2, response[0]["created"])

  def test_update_audit_with_control(self):
    """Test import of existing Audit with mapped Control Snapshot."""
    with factories.single_commit():
      program = factories.ProgramFactory()
      audit = factories.AuditFactory(program=program)
      audit_id = audit.id
      control = factories.ControlFactory()
      factories.RelationshipFactory(source=program, destination=control)
      snapshot = self._create_snapshots(audit, [control])[0]
      factories.RelationshipFactory(source=audit, destination=snapshot)

    response = self.import_data(OrderedDict([
        ("object_type", "Audit"),
        ("Code*", audit.slug),
        ("Title", "New Title"),
        ("Audit Captains", "user@example.com"),
        ("Program", program.slug),
        ("map:control versions", control.slug),
    ]))
    self._check_csv_response(response, {})
    audit = all_models.Audit.query.get(audit_id)
    self.assertEqual(audit.title, "New Title")

  def test_create_audit_with_control(self):
    """Test import of new Audit with mapped Control Snapshot."""
    with factories.single_commit():
      program = factories.ProgramFactory()
      control = factories.ControlFactory()
      factories.RelationshipFactory(source=program, destination=control)

    response = self.import_data(OrderedDict([
        ("object_type", "Audit"),
        ("Code*", ""),
        ("Title", "New Audit"),
        ("State", "Planned"),
        ("Audit Captains", "user@example.com"),
        ("Program", program.slug),
        ("map:control versions", control.slug),
    ]))
    self._check_csv_response(response, {})
    self.assertEqual(all_models.Audit.query.count(), 1)

  def test_ignore_changed_program_during_audit_import(self):
    """Test whether audit's program remains the same (new value is ignored)
    after updating audit by importing it with changed program field"""
    with factories.single_commit():
      original_program = factories.ProgramFactory()
      original_program_slug = original_program.slug
      audit = factories.AuditFactory(program=original_program)
      new_program = factories.ProgramFactory()

    self.import_data(OrderedDict([
            ("object_type", "Audit"),
            ("Code", audit.slug),
            ("Title", audit.title),
            ("State", "In Progress"),
            ("Audit Captains", "user@example.com"),
            ("Program", new_program.slug),
            ("map:control versions", ""),
    ]))
    actual_program_slug = all_models.Audit.query.get(audit.id).program.slug
    self.assertEqual(actual_program_slug, original_program_slug)

  def test_show_warning_message_for_import_of_audit_with_changed_program(self):
    """Test whether warning message occurred
    after attempt of changing program for existing audit by importing it (audit) with changed program field"""
    with factories.single_commit():
      original_program = factories.ProgramFactory()
      audit = factories.AuditFactory(program=original_program)
      new_program = factories.ProgramFactory()

    response = self.import_data(OrderedDict([
            ("object_type", "Audit"),
            ("Code", audit.slug),
            ("Title", audit.title),
            ("State", "In Progress"),
            ("Audit Captains", "user@example.com"),
            ("Program", new_program.slug),
            ("map:control versions", ""),
    ]))

    expected_warnings = {
        'Audit': {
            'row_warnings': {
                errors.UNMODIFIABLE_COLUMN.format(
                    line=3,
                    column_name=original_program.type
                )
            },
        }
    }
    self._check_csv_response(response, expected_warnings)
