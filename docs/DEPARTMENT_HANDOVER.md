# SGSITS Electrical Engineering timetable — department handover

## 1. Roles and ownership

- **Administrator:** owns institute data, academic terms, faculty, rooms, availability, reservations, subjects, generation, publication, rescheduling, accounts and backups.
- **Faculty:** read-only access to their faculty timetable, directories and downloads. Faculty report requested changes to the administrator.
- **Student:** read-only access to the published timetable associated with the account's semester or batch group.

Only SGSITS-domain accounts can be created. The administrator links each faculty login to one faculty record and each student login to a semester or batch group such as `SEM-3` or `SEM-3-B1`.

## 2. Initial department setup

1. Sign in as administrator and open **Start Setup**.
2. Confirm institute, department, Odd/Even academic term, working days, periods and the manually selected lunch break.
3. Review faculty workload limits and rooms/labs. A room can support multiple subject capabilities and simultaneous groups.
4. Configure the three active semester cohorts and their home-room policies.
5. Enter each subject's theory, lecture/tutorial and practical frequency, assigned faculty, elective group, batches and eligible rooms.
6. Record faculty/room unavailability with written reasons and add fixed reservations.
7. Run **Cross-check configuration** and resolve every blocker before generation.

Do not delete one term to configure the other. Create and activate separate Odd and Even academic-term records; each retains its own timetable history.

## 3. Generation and approval

1. Generate all three semester timetables together.
2. Open **Timetable** and review the independent validation card. A version is ready for review only when all hard constraints pass.
3. Check student gaps, faculty gaps, room changes, room utilization, laboratories, electives and daily balance.
4. Print semester view for one semester per portrait A4 page or select faculty view for an individual teaching schedule.
5. Mark the approved version **Published**. Older versions remain immutable and may be archived without deletion.

If generation fails, the Generate page shows exact preprocessing/solver diagnostics. Correct the named faculty, room, subject or time constraint and run generation again.

## 4. Accounts and passwords

- Administrators create and edit accounts under **User Access**. Leaving the password field blank while editing preserves the existing password; entering a new password performs an administrator reset.
- Every signed-in user can change their own password under **My Account** after providing the current password.
- Deactivate an account when temporary access should stop. The current administrator cannot deactivate or delete their own account.
- Department data is not owned by an individual login. Changing or replacing an administrator account does not remove faculty, rooms, subjects or timetable history.

## 5. Backup, starter copy and restoration

- Download **Private backup** before important edits and after approving a timetable. It contains all data and password hashes and must be stored securely.
- Download **Starter database** for a new department installation. It retains academic/master data and timetable history but removes every login, allowing the receiving department to create its own first administrator.
- Use **Restore backup** only with a private backup. The server checks SQLite integrity, required schema and the presence of an active administrator. It also creates `backups/pre-restore-<timestamp>.db` before replacing the live database.
- After restoration, sign in with an administrator account contained in the restored backup.

Automatic timetable JSON snapshots are created for every generated or approved rescheduled version and can be downloaded from the Timetable page. These snapshots complement, but do not replace, full database backups.

## 6. Routine operating checklist

- At term start: create/activate the academic term, review master data and download a private backup.
- Before generation: close faculty change requests, enter all availability/reservations, and cross-check setup.
- After generation: inspect validation metrics, print review copies, publish the approved version and download another private backup.
- For a disruption: use **Reschedule**, preview changes, verify diagnostics, then apply. A new version is created while the previous one remains preserved.
- At academic-year close: mark the achieved timetable Published/Archived, retain its database and JSON backups, then create the next term without deleting history.
