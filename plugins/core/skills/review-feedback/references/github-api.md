# GitHub calls

All through `gh`, as `robinbryce` in every scope. Write JSON bodies to a
file in `$CLAUDE_JOB_DIR/tmp` or `/tmp/review-feedback/` and pass `-F
body=@<file>`; inline mutation bodies tend to get blocked.

## Who am I

```bash
gh api user --jq .login            # must equal the PR author for this skill to act
```

## Threads, reviews, requests (one query)

```bash
gh api graphql -F owner=<o> -F name=<r> -F number=<n> -f query='
query($owner:String!,$name:String!,$number:Int!){ repository(owner:$owner,name:$name){
  pullRequest(number:$number){
    reviewDecision isDraft headRefOid author{login}
    reviewRequests(first:20){ nodes{ requestedReviewer{ ... on User{login} ... on Bot{login} } } }
    reviewThreads(first:100){ nodes{ id isResolved isOutdated path line
      comments(first:20){ nodes{ databaseId body author{login} createdAt url } } } }
    latestReviews(first:20){ nodes{ state submittedAt author{login} body } }
    comments(last:50){ nodes{ databaseId body author{login} createdAt } } } } }'
```

Verified 2026-10-25 against SentientDogs/flip-oracle#1672. Unresolved
Threads: `isResolved == false`. A Thread's first comment is the Finding; later
comments are the conversation. Robin's own replies carry the marker.

## The marker

Every reply the skill posts ends with a hidden line:

```
<!-- review-feedback: <short sha or ISSUE-ID> -->
```

The newest marker SHA across all replies is "the last commit the skill
pushed"; comments after it are new Feedback.

## Reply on a Thread

```bash
gh api repos/<o>/<r>/pulls/<n>/comments/<first comment databaseId>/replies -F body=@reply.md
```

## Resolve a Thread

```bash
gh api graphql -F id=<thread node id> -f query='
mutation($id:ID!){ resolveReviewThread(input:{threadId:$id}){ thread{ isResolved } } }'
```

## PR-level comment (tick summary) and re-review

```bash
gh pr comment <n> -R <o>/<r> --body-file summary.md
gh pr edit <n> -R <o>/<r> --add-reviewer <login>[,<login>]
```

## Push

```bash
git push origin HEAD                 # never --force; the branch is the PR's head
```
