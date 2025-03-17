#!groovy
pipeline {
	agent { label 'build-zenoss-product' }
    // parameters {
    //     credentials(
    //         credentialType: 'com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl',
    //         defaultValue: '59439429-e8f4-442a-ace7-122701c36e2b',
    //         description: '',
    //         name: 'GIT_CREDENTIAL_ID',
    //         required: false
    //     )
    // }
    environment {
        GIT_CREDENTIAL_ID = '59439429-e8f4-442a-ace7-122701c36e2b'
        BRANCH = "${sh(returnStdout: true, script: "git name-rev --name-only HEAD").trim()}"
        ASSEMBLY_BRANCH = "${sh(returnStdout: true, script: "cat ASSEMBLY").trim()}"
    }
	stages {
		stage("Configure") {
			steps {
                echo "Using BRANCH=${env.BRANCH}"
                echo "Using ASSEMBLY_BRANCH=${env.ASSEMBLY_BRANCH}"
				deleteDir()
                dir("zenoss-prodbin") {
                    checkout([
                        $class: 'GitSCM',
                        branches: [[name: BRANCH]],
                        extensions: [[$class: 'LocalBranch', localBranch: BRANCH]],
                        userRemoteConfigs: [[
                            credentialsId: GIT_CREDENTIAL_ID,
                            url: 'https://github.com/zenoss/zenoss-prodbin'
                        ]]
                    ])
                }
                dir("product-assembly") {
                    checkout([
                        $class: 'GitSCM',
                        branches: [[name: ASSEMBLY_BRANCH]],
                        extensions: [[$class: 'LocalBranch', localBranch: ASSEMBLY_BRANCH]],
                        userRemoteConfigs: [[
                            credentialsId: GIT_CREDENTIAL_ID,
                            url: 'https://github.com/zenoss/product-assembly'
                        ]]
                    ])
                }
			}
		}
		stage("Build") {
			steps {
				dir("zenoss-prodbin") {
					sh("make")
				}
			}
		}
		stage("Test") {
			steps {
				dir("zenoss-prodbin/ci") {
					sh("make")
				}
			}
		}
        stage("Archive") {
            when { not { changeRequest() } }
            steps {
                archiveArtifacts artifacts: "zenoss-prodbin/dist/*"
            }
        }
        stage("Publish") {
            when { anyOf { branch 'master'; branch 'master-6.x' } }
            steps {
                sshPublisher(
                    publishers: [
                        sshPublisherDesc(
                            configName: 'zenpip',
                            transfers: [
                                sshTransfer(
                                    cleanRemote: false,
                                    excludes: '',
                                    execCommand: '',
                                    execTimeout: 120000,
                                    flatten: false,
                                    makeEmptyDirs: false,
                                    noDefaultExcludes: false,
                                    patternSeparator: '[, ]+',
                                    remoteDirectory: '',
                                    remoteDirectorySDF: false,
                                    removePrefix: 'zenoss-prodbin/dist/',
                                    sourceFiles: 'zenoss-prodbin/dist/*.whl'
                                )
                            ],
                            usePromotionTimestamp: false,
                            useWorkspaceInPromotion: false,
                            verbose: false
                        )
                    ]
                )
            }
        }
	}
}
