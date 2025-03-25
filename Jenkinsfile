#!groovy
pipeline {
    agent { label 'build-zenoss-product' }
    environment {
        GIT_CREDENTIAL_ID = '59439429-e8f4-442a-ace7-122701c36e2b'
        ASSEMBLY_BRANCH = "${sh(returnStdout: true, script: "cat ASSEMBLY").trim()}"
    }
    stages {
        stage("Configure") {
            steps {
                echo "Using ASSEMBLY_BRANCH=${env.ASSEMBLY_BRANCH}"
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
                sh("make")
            }
        }
        stage("Test") {
            steps {
                dir("ci") {
                    sh("make")
                }
            }
        }
        stage("Archive") {
            when { not { changeRequest() } }
            steps {
                archiveArtifacts artifacts: "dist/*"
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
                                    removePrefix: 'dist/',
                                    sourceFiles: 'dist/*.whl'
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
