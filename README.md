# ansible-google-modules

## gcs_bucket

Create/delete bucket, manage ACL, default ACL or IAM policies.
Supports check mode, as well as shows detailed diff for policies.

Requires `google-cloud-storage` to be installed.

Example usage:

    - name: create bucket
      gcs_bucket:
        state: present
        name: chemikadze-test-ansible
        acl:
          - entity: user-chemikadze@gmail.com
            role: OWNER
        iam_policy:
          - member: user:chemikadze@gmail.com
            role: roles/storage.objectAdmin
            
Example result:

    changed: [localhost] => {
        "bucket": {
            "acl": [
                {
                    "entity": "project-editors-576872418101", 
                    "role": "OWNER"
                }, 
                {
                    "entity": "project-owners-576872418101", 
                    "role": "OWNER"
                }, 
                {
                    "entity": "project-viewers-576872418101", 
                    "role": "READER"
                }, 
                {
                    "entity": "user-chemikadze@gmail.com", 
                    "role": "OWNER"
                }
            ], 
            "default_acl": [
                {
                    "entity": "project-editors-576872418101", 
                    "role": "OWNER"
                }, 
                {
                    "entity": "project-owners-576872418101", 
                    "role": "OWNER"
                }, 
                {
                    "entity": "project-viewers-576872418101", 
                    "role": "READER"
                }
            ], 
            "iam_policy": {
                "roles/storage.legacyBucketOwner": [
                    "user:chemikadze@gmail.com", 
                    "projectOwner:chemikadze-internal", 
                    "projectEditor:chemikadze-internal"
                ], 
                "roles/storage.legacyBucketReader": [
                    "projectViewer:chemikadze-internal"
                ], 
                "roles/storage.objectAdmin": [
                    "user:chemikadze@gmail.com"
                ]
            }, 
            "location": "US-WEST1", 
            "name": "chemikadze-test-ansible", 
            "project_number": 576872418101, 
            "storage_class": "STANDARD"
        }, 
        "changed": true, 
        "changes": {
            "acl": {
                "added": [
                    [
                        "user-chemikadze@gmail.com", 
                        "OWNER"
                    ]
                ], 
                "changed": true, 
                "removed": []
            }, 
            "default_acl": {
                "added": [], 
                "changed": false, 
                "removed": []
            }, 
            "iam_policy": {
                "added": [
                    [
                        "roles/storage.objectAdmin", 
                        "user:chemikadze@gmail.com"
                    ]
                ], 
                "changed": true, 
                "removed": []
            }
        }, 
        "invocation": {
            "module_args": {
                "acl": [
                    {
                        "entity": "user-chemikadze@gmail.com", 
                        "role": "OWNER"
                    }
                ], 
                "default_acl": [], 
                "force": false, 
                "iam_policy": [
                    {
                        "member": "user:chemikadze@gmail.com", 
                        "role": "roles/storage.objectAdmin"
                    }
                ], 
                "location": "US-WEST1", 
                "name": "chemikadze-test-ansible", 
                "project": null, 
                "reset_acl": false, 
                "reset_default_acl": false, 
                "reset_iam_policy": false, 
                "state": "present", 
                "storage_class": "STANDARD"
            }
        }, 
        "state": "present"
    }