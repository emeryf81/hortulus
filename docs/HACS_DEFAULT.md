# Getting Hortulus into the HACS default list

Today Hortulus is installed as a *custom repository* in HACS. Once it is in the
[HACS default list](https://github.com/hacs/default), anyone can find it by name in HACS. Two pull
requests are needed: one to home-assistant/brands (step 1) and one to hacs/default (step 2). HACS accepts the
second one only from the owner of the repository or a major contributor to it.

## Checklist (state on 2026-10-21)

| Requirement | State |
|---|---|
| Public repository with a description and topics | ✅ "Hortulus – kitchen garden and greenhouse management for Home Assistant"; topics include `home-assistant`, `hacs-integration` |
| License | ✅ MIT |
| `hacs.json` with name and minimum Home Assistant version | ✅ `2025.10.0` (CI tests that version **and** the pinned current one) |
| `manifest.json` with `version`, `codeowners`, `documentation`, `issue_tracker` | ✅ |
| hassfest passes | ✅ |
| The HACS action passes without errors or ignores | ⏳ passes, but still with `ignore: brands`: complete after step 1 |
| At least one GitHub release (not just a tag) | ✅ the release workflow publishes one for every version on `main` |
| Brand images in `home-assistant/brands` | ⏳ step 1 |
| Listed in `hacs/default` | ⏳ step 2 |

## Step 1 – brand images (home-assistant/brands)

1. Fork <https://github.com/home-assistant/brands>.
2. Add the folder `custom_integrations/garden_manager/` with these files from `assets/brand/`:
   `icon.png` (256×256), `icon@2x.png` (512×512), `logo.png` (780×200), `logo@2x.png` (1560×400),
   `dark_logo.png` (780×200, for the dark theme). All are transparent PNGs, trimmed, without padding.
3. Open the pull request with the title `Add Hortulus Garden Manager (garden_manager)` and fill in
   their template (domain `garden_manager`, link to this repository).
4. Once it is merged, remove `ignore: brands` from the HACS job in `.github/workflows/ci.yml`.

## Step 2 – the default list (hacs/default)

1. Fork <https://github.com/hacs/default>.
2. Add `emeryf81/hortulus` to the `integration` file, in alphabetical order (one line, no trailing comma problems).
3. Open the pull request: title `Adds new integration [emeryf81/hortulus]`, link to the latest release and to a
   green run of the HACS action, and tick the boxes in their template.
4. The HACS bot checks the repository. After the merge, Hortulus shows up in HACS under its own name at the next
   scheduled HACS scan (not right away), and users can then drop the custom repository entry.
