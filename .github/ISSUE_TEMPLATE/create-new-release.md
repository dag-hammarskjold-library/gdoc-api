---
name: Create new release
about: Tasks for creating a new realase
title: Create new release
labels: ''
assignees: ''

---

- [ ] Ensure all other issues in the milestone have been closed or removed
- [ ] Update setup.py to new version number
- [ ] Create a new release, with the release name and the tag named after the new version
- [ ] Ensure that the workflow triggered by the release completes successfully
- [ ] Issue a PR updating the main branch version to the new dev version (`<version>.dev`) in setup.py, closing this issue

