# Navigation on Frappe v16.5x

The Education module ships its curated navigation as a standard `Sidebar` at
`education/education/sidebar/education/education.json`. Frappe imports it during
`bench --site <site> migrate` and filters its destinations using the signed-in
user's permissions. It uses the existing `Education` module and workspace.

The previous app-level `workspace_sidebar` export is removed because recent v16
releases retain that DocType as a migration archive and no longer import those
exports. The desktop-grid icon points to the same native Sidebar, while the Apps
screen continues to use `add_to_apps_screen` in `hooks.py`.

The menu includes Admission Register, Subject, Course Enrollment, Subject
Registration, Fee Term and Fee Plan. Repeated Student Batch destinations are
collapsed. Application access follows read access to Education documents; each
sidebar destination remains subject to Frappe permissions.

Deploy the fork with `git pull --ff-only`, then run `bench --site <site> migrate`
and `bench build --app education`. No new workspace or Custom Field is created
by this navigation update. The application's existing integration fields remain
managed by Education itself.
