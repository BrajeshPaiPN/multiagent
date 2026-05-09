// ==========================================
// Neo4j Database Initialization Script
// ==========================================
// Run this in your Neo4j AuraDB Workspace console BEFORE running the Python system.
// This creates the conflict-preserving schema and test data for Anticipatory Bail.

// Step 1: Clear existing data for a clean slate
MATCH (n) DETACH DELETE n;

// Step 2: Create the core Legal Concept
CREATE (concept:LegalIssue {name: "Anticipatory Bail", section: "BNSS 482"})

// Step 3: Create Case 1 (The Bad Law — will be overruled)
CREATE (case1:Precedent {name: "State v. Sharma", year: 2022, verdict: "Granted anticipatory bail based on verbal threat."})

// Step 4: Create Case 2 (The Good Law that overrules Case 1)
CREATE (case2:Precedent {name: "Union v. Singh", year: 2024, verdict: "Denied anticipatory bail. Verbal threats without evidence are insufficient."})

// Step 5: Map relationships — both cases apply to the same legal issue
CREATE (case1)-[:APPLIES_TO]->(concept)
CREATE (case2)-[:APPLIES_TO]->(concept)

// Step 6: Create the OVERRULES edge — this is the AKGP core feature
// This edge tells the Shepardizer that Case 1 is legally dead
CREATE (case2)-[:OVERRULES {reason: "Insufficient evidentiary standard in lower court"}]->(case1)
