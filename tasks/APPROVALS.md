
# LEAD APPROVAL LOG


--------------------------------------------------

# APPROVAL ENTRY FORMAT

request_by:
type:
description:
decision:
approved_by:
date:


--------------------------------------------------

# EXAMPLES

request_by: architect
type: architecture
description: introduce service layer for task module
decision: approved
approved_by: lead


request_by: developer
type: dependency
description: add sqlx crate
decision: approved
approved_by: lead


request_by: developer
type: dependency
description: add kafka crate
decision: rejected
approved_by: lead
reason: not required for current feature
