import subprocess
import sys
from pathlib import Path

from snake_case_migration.manifest import Manifest, Mapping, save_manifest
from snake_case_migration.rewrite_rst import iter_rst_files, rewrite_rst_python_source


def _manifest() -> Manifest:
    return Manifest(
        mappings=[
            Mapping(kind="function", old="generateTrajectory", new="generate_trajectory", source="test"),
            Mapping(kind="method", old="teleopPeriodic", new="teleop_periodic", source="test"),
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
            Mapping(kind="method", old="getDefault", new="get_default", source="test"),
            Mapping(kind="attribute", old="kForward", new="FORWARD", source="test"),
        ]
    )


def test_rewrite_rst_python_fenced_blocks_only():
    source = """.. tab-set-code::

   ```java
   public void teleopPeriodic() {
     table.getDoubleTopic("x");
   }
   ```

   ```c++
   void TeleopPeriodic() {
     table->GetDoubleTopic("x");
   }
   ```

   ```python
   def generateTrajectory(table):
       table.getDoubleTopic("x")
   ```
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. tab-set-code::

   ```java
   public void teleopPeriodic() {
     table.getDoubleTopic("x");
   }
   ```

   ```c++
   void TeleopPeriodic() {
     table->GetDoubleTopic("x");
   }
   ```

   ```python
   def generate_trajectory(table):
       table.get_double_topic("x")
   ```
"""


def test_rewrite_rst_code_block_python_body_only():
    source = """Before ``getDefault`` stays unchanged.

.. code-block:: python
   :linenos:

   def generateTrajectory():
       mode = wpilib.Relay.Value.kForward

.. code-block:: java

   NetworkTableInstance.getDefault();
"""

    assert rewrite_rst_python_source(source, _manifest()) == """Before ``getDefault`` stays unchanged.

.. code-block:: python
   :linenos:

   def generate_trajectory():
       mode = wpilib.Relay.Value.FORWARD

.. code-block:: java

   NetworkTableInstance.getDefault();
"""


def test_rewrite_rst_python_tab_preserves_remote_literal_include_blocks():
    source = """.. tab-set::

   .. tab-item:: Python

      Before include, use ``getDefault``.

      .. remoteliteralinclude:: https://raw.githubusercontent.com/example/robot/getDefault.py
         :language: python
         :tag: getDoubleTopic

      After include, use ``teleopPeriodic``.
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. tab-set::

   .. tab-item:: Python

      Before include, use ``get_default``.

      .. remoteliteralinclude:: https://raw.githubusercontent.com/example/robot/getDefault.py
         :language: python
         :tag: getDoubleTopic

      After include, use ``teleop_periodic``.
"""


def test_rewrite_rst_python_tab_preserves_case_insensitive_remote_literal_include_blocks():
    source = """.. tab-set::

   .. tab-item:: Python

      .. RemoteLiteralInclude:: https://raw.githubusercontent.com/example/robot/getDefault.py
         :language: python
         :tag: getDoubleTopic

      After include, use ``teleopPeriodic``.
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. tab-set::

   .. tab-item:: Python

      .. RemoteLiteralInclude:: https://raw.githubusercontent.com/example/robot/getDefault.py
         :language: python
         :tag: getDoubleTopic

      After include, use ``teleop_periodic``.
"""


def test_rewrite_rst_python_tab_preserves_rli_alias_blocks():
    source = """.. tab-set::

   .. tab-item:: Python

      Before include, use ``getDefault``.

      .. rli:: https://raw.githubusercontent.com/example/robot/getDefault.py
         :language: python
         :tag: getDoubleTopic

      After include, use ``teleopPeriodic``.
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. tab-set::

   .. tab-item:: Python

      Before include, use ``get_default``.

      .. rli:: https://raw.githubusercontent.com/example/robot/getDefault.py
         :language: python
         :tag: getDoubleTopic

      After include, use ``teleop_periodic``.
"""


def test_rewrite_rst_python_code_block_preserves_directive_options():
    source = """.. code-block:: python
   :linenos:
   :caption: getDefault example
   :name: getDoubleTopic-snippet

   def generateTrajectory():
       return ntcore.NetworkTableInstance.getDefault()
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. code-block:: python
   :linenos:
   :caption: getDefault example
   :name: getDoubleTopic-snippet

   def generate_trajectory():
       return ntcore.NetworkTableInstance.get_default()
"""


def test_rewrite_rst_python_code_block_preserves_multiline_directive_options():
    source = """.. code-block:: python
   :caption: getDefault example
      continuation getDoubleTopic
   :name: teleopPeriodic-snippet

   def generateTrajectory():
       return ntcore.NetworkTableInstance.getDefault()
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. code-block:: python
   :caption: getDefault example
      continuation getDoubleTopic
   :name: teleopPeriodic-snippet

   def generate_trajectory():
       return ntcore.NetworkTableInstance.get_default()
"""


def test_rewrite_rst_non_python_tab_scans_nested_python_code_blocks():
    source = """.. tab-set::

   .. tab-item:: Java

      Non-Python prose keeps ``getDefault`` unchanged.

      .. code-block:: python

         def generateTrajectory():
             return ntcore.NetworkTableInstance.getDefault()

      ```python
      table.getDoubleTopic("x")
      ```

      Still non-Python prose keeps ``teleopPeriodic`` unchanged.
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. tab-set::

   .. tab-item:: Java

      Non-Python prose keeps ``getDefault`` unchanged.

      .. code-block:: python

         def generate_trajectory():
             return ntcore.NetworkTableInstance.get_default()

      ```python
      table.get_double_topic("x")
      ```

      Still non-Python prose keeps ``teleopPeriodic`` unchanged.
"""


def test_rewrite_rst_python_tab_rewrites_colon_leading_rst_role_prose():
    source = """.. tab-set::

   .. tab-item:: Python

      :meth:`NetworkTableInstance.getDefault` returns the default instance.
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. tab-set::

   .. tab-item:: Python

      :meth:`NetworkTableInstance.get_default` returns the default instance.
"""


def test_rewrite_rst_python_tab_preserves_plain_literal_block_body():
    source = """.. tab-set::

   .. tab-item:: Python

      Before literal, use ``getDoubleTopic``.

      Example::

         table.getDoubleTopic("x")
         def teleopPeriodic(self):
             pass

      After literal, call ``teleopPeriodic``.
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. tab-set::

   .. tab-item:: Python

      Before literal, use ``get_double_topic``.

      Example::

         table.getDoubleTopic("x")
         def teleopPeriodic(self):
             pass

      After literal, call ``teleop_periodic``.
"""


def test_rewrite_rst_tab_item_python_body_only():
    source = """.. tab-set::

   .. tab-item:: Java

      ``getDoubleTopic`` remains Java prose.

      ```java
      table.getDoubleTopic("x");
      ```

   .. tab-item:: Python

      In Python, use ``getDoubleTopic``.

      ```python
      table.getDoubleTopic("x")
      ```
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. tab-set::

   .. tab-item:: Java

      ``getDoubleTopic`` remains Java prose.

      ```java
      table.getDoubleTopic("x");
      ```

   .. tab-item:: Python

      In Python, use ``get_double_topic``.

      ```python
      table.get_double_topic("x")
      ```
"""


def test_rewrite_rst_tab_item_sync_python_body_only():
    source = """.. tab-set::

   .. tab-item:: CTRE-Phoenix6
      :sync: python

      ```python
      def teleopPeriodic(self):
          inst = ntcore.NetworkTableInstance.getDefault()
      ```

   .. tab-item:: CTRE-Phoenix6
      :sync: java

      ```java
      public void teleopPeriodic() {}
      ```
"""

    assert rewrite_rst_python_source(source, _manifest()) == """.. tab-set::

   .. tab-item:: CTRE-Phoenix6
      :sync: python

      ```python
      def teleop_periodic(self):
          inst = ntcore.NetworkTableInstance.get_default()
      ```

   .. tab-item:: CTRE-Phoenix6
      :sync: java

      ```java
      public void teleopPeriodic() {}
      ```
"""


def test_iter_rst_files_finds_rst_only(tmp_path: Path):
    rst = tmp_path / "docs" / "index.rst"
    md = tmp_path / "docs" / "index.md"
    pycache = tmp_path / "docs" / "__pycache__" / "ignored.rst"
    rst.parent.mkdir(parents=True)
    pycache.parent.mkdir(parents=True)
    rst.write_text("ok")
    md.write_text("ignored")
    pycache.write_text("ignored")

    assert iter_rst_files([tmp_path]) == [rst]


def test_rewrite_rst_python_roles_but_not_generic_prose():
    source = (
        "Generic prose ``getDefault`` stays unchanged.\n"
        "Use :external:py:func:`wpilib.deployinfo.getDeployData` for deploy data.\n"
        "Use :py:meth:`ntcore.NetworkTable.getDoubleTopic`.\n"
    )
    manifest = Manifest(
        mappings=[
            Mapping(kind="function", old="getDeployData", new="get_deploy_data", source="test"),
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
            Mapping(kind="method", old="getDefault", new="get_default", source="test"),
        ]
    )

    assert rewrite_rst_python_source(source, manifest) == (
        "Generic prose ``getDefault`` stays unchanged.\n"
        "Use :external:py:func:`wpilib.deployinfo.get_deploy_data` for deploy data.\n"
        "Use :py:meth:`ntcore.NetworkTable.get_double_topic`.\n"
    )


def test_rewrite_rst_python_role_display_text_rewrites_target_only():
    source = ":py:class:`Python <robotpy:wpilib.DriverStation.getAlliance>`\n"
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getAlliance", new="get_alliance", source="test"),
            Mapping(kind="attribute", old="Python", new="PYTHON", source="test"),
        ]
    )

    assert rewrite_rst_python_source(source, manifest) == (
        ":py:class:`Python <robotpy:wpilib.DriverStation.get_alliance>`\n"
    )


def test_rewrite_rst_python_tab_role_display_text_rewrites_target_only():
    source = """.. tab-set::

   .. tab-item:: Python

      :py:class:`Python <robotpy:wpilib.DriverStation.getAlliance>`
"""
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getAlliance", new="get_alliance", source="test"),
            Mapping(kind="attribute", old="Python", new="PYTHON", source="test"),
        ]
    )

    assert rewrite_rst_python_source(source, manifest) == """.. tab-set::

   .. tab-item:: Python

      :py:class:`Python <robotpy:wpilib.DriverStation.get_alliance>`
"""


def test_rewrite_rst_python_roles_preserves_non_python_fenced_blocks():
    source = """```java
// literal docs text: :py:meth:`ntcore.NetworkTable.getDoubleTopic`
```

Use :py:meth:`ntcore.NetworkTable.getDoubleTopic`.
"""
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    assert rewrite_rst_python_source(source, manifest) == """```java
// literal docs text: :py:meth:`ntcore.NetworkTable.getDoubleTopic`
```

Use :py:meth:`ntcore.NetworkTable.get_double_topic`.
"""


def test_rewrite_rst_python_roles_preserves_role_shaped_non_roles():
    source = (
        "Escaped \\:py:meth:`ntcore.NetworkTable.getDoubleTopic` stays.\n"
        "Literal ``:py:meth:`ntcore.NetworkTable.getDoubleTopic``` stays.\n"
        "Role :py:meth:`ntcore.NetworkTable.getDoubleTopic` changes.\n"
    )
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    assert rewrite_rst_python_source(source, manifest) == (
        "Escaped \\:py:meth:`ntcore.NetworkTable.getDoubleTopic` stays.\n"
        "Literal ``:py:meth:`ntcore.NetworkTable.getDoubleTopic``` stays.\n"
        "Role :py:meth:`ntcore.NetworkTable.get_double_topic` changes.\n"
    )


def test_rewrite_rst_python_roles_preserves_untyped_code_block():
    source = """.. code-block::

   literal docs text: :py:meth:`ntcore.NetworkTable.getDoubleTopic`

Use :py:meth:`ntcore.NetworkTable.getDoubleTopic`.
"""
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    assert rewrite_rst_python_source(source, manifest) == """.. code-block::

   literal docs text: :py:meth:`ntcore.NetworkTable.getDoubleTopic`

Use :py:meth:`ntcore.NetworkTable.get_double_topic`.
"""


def test_rewrite_rst_python_roles_preserves_plain_literal_block():
    source = """Example::

   literal docs text: :py:meth:`ntcore.NetworkTable.getDoubleTopic`

Use :py:meth:`ntcore.NetworkTable.getDoubleTopic`.
"""
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    assert rewrite_rst_python_source(source, manifest) == """Example::

   literal docs text: :py:meth:`ntcore.NetworkTable.getDoubleTopic`

Use :py:meth:`ntcore.NetworkTable.get_double_topic`.
"""


def test_rewrite_rst_python_tab_list_item_plain_literal_block_allows_continuation_prose():
    source = """.. tab-set::

   .. tab-item:: Python

      * Example::

          table.getDoubleTopic("x")
          literal docs text: :py:meth:`ntcore.NetworkTable.getDoubleTopic`

        Continue with ``getDoubleTopic`` and :py:meth:`ntcore.NetworkTable.getDoubleTopic`.
"""
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    assert rewrite_rst_python_source(source, manifest) == """.. tab-set::

   .. tab-item:: Python

      * Example::

          table.getDoubleTopic("x")
          literal docs text: :py:meth:`ntcore.NetworkTable.getDoubleTopic`

        Continue with ``get_double_topic`` and :py:meth:`ntcore.NetworkTable.get_double_topic`.
"""


def test_audit_rst_python_source_reports_only_python_labeled_old_names():
    source = """.. tab-set-code::

   ```java
   table.getDoubleTopic("x");
   ```

   ```python
   def generateTrajectory(table):
       self.possibleOldName = table.getDoubleTopic("x")
   ```

Generic prose generateTrajectory stays ignored.
"""
    manifest = Manifest(
        mappings=[
            Mapping(kind="function", old="generateTrajectory", new="generate_trajectory", source="test"),
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    from snake_case_migration.rewrite_rst import audit_rst_python_source

    assert audit_rst_python_source(source, manifest) == [
        "line 8 python: mapped old name 'generateTrajectory' remains; expected 'generate_trajectory'",
        "line 9 python: unmapped camelCase candidate 'possibleOldName'",
        "line 9 python: mapped old name 'getDoubleTopic' remains; expected 'get_double_topic'",
    ]


def test_audit_rst_python_source_reports_python_roles():
    source = (
        "Generic getDeployData stays ignored.\n"
        "Use :external:py:func:`wpilib.deployinfo.getDeployData`.\n"
    )
    manifest = Manifest(
        mappings=[
            Mapping(kind="function", old="getDeployData", new="get_deploy_data", source="test"),
        ]
    )

    from snake_case_migration.rewrite_rst import audit_rst_python_source

    assert audit_rst_python_source(source, manifest) == [
        "line 2 python-role: mapped old name 'getDeployData' remains; expected 'get_deploy_data'"
    ]


def test_audit_rst_python_source_reports_remote_python_includes():
    source = """.. remoteliteralinclude:: https://example.invalid/robot.py
   :language: python

.. remoteliteralinclude:: https://example.invalid/Robot.java
   :language: java
"""

    from snake_case_migration.rewrite_rst import audit_rst_python_source

    assert audit_rst_python_source(source, Manifest()) == [
        "line 1 remote-python-include: https://example.invalid/robot.py is not rewritten"
    ]


def test_audit_rst_python_source_reports_rli_alias_remote_python_includes():
    source = """.. rli:: https://example.invalid/robot.py
   :language: python
   :tag: getDoubleTopic

.. rli:: https://example.invalid/Robot.java
   :language: java
"""

    from snake_case_migration.rewrite_rst import audit_rst_python_source

    assert audit_rst_python_source(source, Manifest()) == [
        "line 1 remote-python-include: https://example.invalid/robot.py is not rewritten"
    ]


def test_audit_rst_python_source_scans_nested_python_blocks_in_non_python_tabs():
    source = """.. tab-set::

   .. tab-item:: Java

      Java prose getDoubleTopic stays ignored.

      .. code-block:: python

         table.getDoubleTopic("x")

      ```python
      generateTrajectory(table)
      ```
"""
    manifest = Manifest(
        mappings=[
            Mapping(kind="function", old="generateTrajectory", new="generate_trajectory", source="test"),
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    from snake_case_migration.rewrite_rst import audit_rst_python_source

    assert audit_rst_python_source(source, manifest) == [
        "line 9 python: mapped old name 'getDoubleTopic' remains; expected 'get_double_topic'",
        "line 12 python: mapped old name 'generateTrajectory' remains; expected 'generate_trajectory'",
    ]


def test_audit_rst_python_source_ignores_code_block_options():
    source = """.. code-block:: python
   :caption: getDoubleTopic example
   :name: getDoubleTopic-snippet

   table.getDoubleTopic("x")
"""
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    from snake_case_migration.rewrite_rst import audit_rst_python_source

    assert audit_rst_python_source(source, manifest) == [
        "line 5 python: mapped old name 'getDoubleTopic' remains; expected 'get_double_topic'"
    ]


def test_audit_rst_python_source_skips_remote_include_and_plain_literal_bodies_in_python_tabs():
    source = """.. tab-set::

   .. tab-item:: Python

      .. RemoteLiteralInclude:: https://example.invalid/getDoubleTopic.py
         :language: python
         :tag: getDoubleTopic

      Example::

         table.getDoubleTopic("x")

      After getDoubleTopic remains.
"""
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    from snake_case_migration.rewrite_rst import audit_rst_python_source

    assert audit_rst_python_source(source, manifest) == [
        "line 5 remote-python-include: https://example.invalid/getDoubleTopic.py is not rewritten",
        "line 13 python: mapped old name 'getDoubleTopic' remains; expected 'get_double_topic'",
    ]


def test_audit_rst_python_source_ignores_escaped_and_inline_literal_python_roles():
    source = (
        "Escaped \\:py:meth:`ntcore.NetworkTable.getDoubleTopic` stays.\n"
        "Literal ``:py:meth:`ntcore.NetworkTable.getDoubleTopic``` stays.\n"
        "Role :py:meth:`ntcore.NetworkTable.getDoubleTopic` remains.\n"
    )
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    from snake_case_migration.rewrite_rst import audit_rst_python_source

    assert audit_rst_python_source(source, manifest) == [
        "line 3 python-role: mapped old name 'getDoubleTopic' remains; expected 'get_double_topic'"
    ]


def test_audit_rst_python_source_reports_role_on_plain_literal_introducer_only():
    source = """See :py:meth:`ntcore.NetworkTable.getDoubleTopic`::

   table.getDoubleTopic("x")
"""
    manifest = Manifest(
        mappings=[
            Mapping(kind="method", old="getDoubleTopic", new="get_double_topic", source="test"),
        ]
    )

    from snake_case_migration.rewrite_rst import audit_rst_python_source

    assert audit_rst_python_source(source, manifest) == [
        "line 1 python-role: mapped old name 'getDoubleTopic' remains; expected 'get_double_topic'"
    ]


def test_cli_rewrite_rst_python_dry_run_and_write(tmp_path: Path):
    manifest_path = tmp_path / "manifest.toml"
    docs_path = tmp_path / "docs.rst"
    save_manifest(
        manifest_path,
        Manifest(
            mappings=[
                Mapping(
                    kind="function",
                    old="generateTrajectory",
                    new="generate_trajectory",
                    source="test",
                ),
            ]
        ),
    )
    docs_path.write_text("""```python
def generateTrajectory():
    pass
```
""")

    dry_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "snake_case_migration",
            "--manifest",
            str(manifest_path),
            "rewrite-rst-python",
            str(docs_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert dry_run.returncode == 0
    assert str(docs_path) in dry_run.stdout
    assert "generateTrajectory" in docs_path.read_text()

    write_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "snake_case_migration",
            "--manifest",
            str(manifest_path),
            "rewrite-rst-python",
            "--write",
            str(docs_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert write_run.returncode == 0
    assert "def generate_trajectory" in docs_path.read_text()


def test_cli_audit_rst_python_exits_nonzero_for_findings(tmp_path: Path):
    manifest_path = tmp_path / "manifest.toml"
    docs_path = tmp_path / "docs.rst"
    save_manifest(
        manifest_path,
        Manifest(
            mappings=[
                Mapping(
                    kind="function",
                    old="generateTrajectory",
                    new="generate_trajectory",
                    source="test",
                ),
            ]
        ),
    )
    docs_path.write_text("""```python
def generateTrajectory():
    pass
```
""")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "snake_case_migration",
            "--manifest",
            str(manifest_path),
            "audit-rst-python",
            str(docs_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 1
    assert str(docs_path) in result.stdout
    assert "generateTrajectory" in result.stdout


def test_cli_rewrite_rst_python_all_scopes_applies_scoped_mappings(tmp_path: Path):
    manifest_path = tmp_path / "manifest.toml"
    docs_path = tmp_path / "frc-docs" / "docs.rst"
    docs_path.parent.mkdir()
    save_manifest(
        manifest_path,
        Manifest(
            mappings=[
                Mapping(
                    kind="method",
                    old="arcadeDrive",
                    new="arcade_drive",
                    source="test",
                    scope="robotpy",
                ),
            ]
        ),
    )
    docs_path.write_text("""```python
drive.arcadeDrive(1, 0)
```
""")

    default_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "snake_case_migration",
            "--manifest",
            str(manifest_path),
            "rewrite-rst-python",
            "--write",
            str(docs_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert default_run.returncode == 0
    assert "arcadeDrive" in docs_path.read_text()

    all_scopes_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "snake_case_migration",
            "--manifest",
            str(manifest_path),
            "rewrite-rst-python",
            "--all-scopes",
            "--write",
            str(docs_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert all_scopes_run.returncode == 0
    assert "arcade_drive" in docs_path.read_text()


def test_cli_audit_rst_python_all_scopes_reports_scoped_mappings(tmp_path: Path):
    manifest_path = tmp_path / "manifest.toml"
    docs_path = tmp_path / "frc-docs" / "docs.rst"
    docs_path.parent.mkdir()
    save_manifest(
        manifest_path,
        Manifest(
            mappings=[
                Mapping(
                    kind="method",
                    old="getRawAxis",
                    new="get_raw_axis",
                    source="test",
                    scope="robotpy",
                ),
            ]
        ),
    )
    docs_path.write_text("""```python
joystick.getRawAxis(0)
```
""")

    default_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "snake_case_migration",
            "--manifest",
            str(manifest_path),
            "audit-rst-python",
            str(docs_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert default_run.returncode == 1
    assert "unmapped camelCase candidate 'getRawAxis'" in default_run.stdout
    assert "mapped old name 'getRawAxis'" not in default_run.stdout

    all_scopes_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "snake_case_migration",
            "--manifest",
            str(manifest_path),
            "audit-rst-python",
            "--all-scopes",
            str(docs_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert all_scopes_run.returncode == 1
    assert str(docs_path) in all_scopes_run.stdout
    assert "mapped old name 'getRawAxis' remains; expected 'get_raw_axis'" in all_scopes_run.stdout
