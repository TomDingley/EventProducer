
module EDM4HepOutput EDM4HepOutput {
    add ReconstructedParticleCollections EFlowTrack EFlowPhoton EFlowNeutralHadron ParticleFlowCandidates
    add GenParticleCollections           Particle
    add JetCollections                   Jet JetNoIso ParticleFlowJet08 ParticleFlowJet15 TrackJet02 GenJet04
    add MuonCollections                  Muon MuonNoIso 
    add ElectronCollections              Electron ElectronNoIso 
    add PhotonCollections                Photon PhotonNoIso 
    add MissingETCollections             MissingET GenMissingET
    add ScalarHTCollections              ScalarHT
    set RecoParticleCollectionName       ReconstructedParticles
    set RecoMCParticleLinkCollectionName MCRecoAssociations
}
