/**
 * DUMMY DATA - replace with the real backend.
 *
 * These records are SAMPLES built only from the public challenge description
 * ("Flame in Freefall"). They exist so every screen can be developed before the
 * FastAPI backend is ready. They are NOT verified PSI extractions:
 *  - every `source_url` points to the general PSI repository page, not the real record page;
 *  - `source_id` values are placeholders;
 *  - fields we do not know are `null`, on purpose, to exercise the "Not reported" states.
 *
 * When the backend is ready, set NEXT_PUBLIC_USE_MOCK=false and this file is no longer used.
 */
import { CHALLENGE_URL, PSI_REPO_URL } from "@/lib/constants";
import type { FileRef, FuelClass, Investigation, SourceCitation } from "@/lib/types";

export const TOPICS = [
  "Material flammability",
  "Fire suppression",
  "Smoke & aerosol detection",
  "Flame structure",
  "Oxygen & airflow effects",
  "Droplet combustion",
  "Electric-field effects",
];

export const FUEL_CLASSES: FuelClass[] = ["Solid", "Gas", "Liquid droplet", "Particulate / aerosol"];

const INGESTED_AT = "2026-11-12";

const challengeCitation = (location: string): SourceCitation => ({
  source_name: "NASA Space Apps 2026 challenge background (sample data)",
  source_url: CHALLENGE_URL,
  doi: null,
  location,
  accessed_at: "2026-11-14",
});

const placeholderFile = (id: string, title: string): FileRef => ({
  id: `${id}-file-1`,
  title,
  file_type: "PDF",
  description: "Placeholder entry. The real backend will list reviewed PSI files here.",
  source_url: PSI_REPO_URL,
  reviewed: false,
});

/** Fields shared by all sample records, so each record below stays short. */
function sample(
  partial: Pick<Investigation, "id" | "title" | "acronym" | "summary"> &
    Partial<Investigation>,
): Investigation {
  return {
    source_id: `PSI-SAMPLE-${partial.acronym ?? partial.id}`,
    research_area: "Combustion Science",
    project_type: null,
    platform: "International Space Station",
    environment: "Microgravity",
    hardware: null,
    fuel_classes: [],
    fuel_materials: [],
    topic_tags: [],
    measurement_types: [],
    conditions: [],
    files: [],
    publications: [],
    source_url: PSI_REPO_URL,
    doi: null,
    source_updated_at: null,
    ingested_at: INGESTED_AT,
    data_status: "sample",
    ...partial,
  };
}

const MSG_DUCT = "Microgravity Science Glovebox (MSG), modular fan-driven flow duct built for SPICE";
const CIR_MDCA = "Multi-user Droplet Combustion Apparatus (MDCA) in the Combustion Integrated Rack (CIR)";
const CIR_ACME = "Modular ACME hardware in the Combustion Integrated Rack (CIR)";

export const MOCK_INVESTIGATIONS: Investigation[] = [
  sample({
    id: "psi-bass",
    title: "Burning and Suppression of Solids",
    acronym: "BASS",
    summary:
      "Studies the flammability of solid materials such as fabrics and plastics in microgravity, where oxygen concentration and air flow strongly affect burning.",
    hardware: MSG_DUCT,
    fuel_classes: ["Solid"],
    fuel_materials: ["Fabrics", "Plastics"],
    topic_tags: ["Material flammability", "Oxygen & airflow effects"],
    measurement_types: ["Flame spread observation"],
    files: [placeholderFile("psi-bass", "BASS investigation overview (placeholder)")],
  }),
  sample({
    id: "psi-bass-ii",
    title: "Burning and Suppression of Solids - II",
    acronym: "BASS-II",
    summary:
      "Second investigation in the BASS series on solid-material flammability, using the same glovebox flow-duct hardware.",
    hardware: MSG_DUCT,
    fuel_classes: ["Solid"],
    fuel_materials: ["Fabrics", "Plastics"],
    topic_tags: ["Material flammability", "Oxygen & airflow effects"],
    measurement_types: ["Flame spread observation"],
  }),
  sample({
    id: "psi-saffire",
    title: "Spacecraft Fire Safety Demonstration",
    acronym: "Saffire",
    summary:
      "Saffire-I, -II and -III investigate material flammability in spacecraft-scale conditions. Platform and hardware details are not captured in this sample record.",
    platform: null,
    environment: null,
    fuel_classes: ["Solid"],
    topic_tags: ["Material flammability"],
  }),
  sample({
    id: "psi-same",
    title: "Smoke and Aerosol Measurement Experiment",
    acronym: "SAME",
    summary:
      "Tested fire detection in microgravity by measuring smoke and aerosol particles produced by overheated or burning materials.",
    platform: null,
    fuel_classes: ["Particulate / aerosol"],
    topic_tags: ["Smoke & aerosol detection"],
    measurement_types: ["Smoke and aerosol measurement"],
  }),
  sample({
    id: "psi-same-r",
    title: "Smoke and Aerosol Measurement Experiment - Reflight",
    acronym: "SAME-R",
    summary:
      "Follow-on to SAME for fire detection in microgravity, using the same smoke and aerosol measurement instrument.",
    platform: null,
    fuel_classes: ["Particulate / aerosol"],
    topic_tags: ["Smoke & aerosol detection"],
    measurement_types: ["Smoke and aerosol measurement"],
  }),
  sample({
    id: "psi-daft",
    title: "Dust and Aerosol Measurement Feasibility Test",
    acronym: "DAFT",
    summary:
      "Used an instrument that also served in SAME and SAME-R, here to detect dust instead of smoke. Still relevant to fire safety, though less directly.",
    platform: null,
    fuel_classes: ["Particulate / aerosol"],
    topic_tags: ["Smoke & aerosol detection"],
    measurement_types: ["Dust and aerosol measurement"],
  }),
  sample({
    id: "psi-flex",
    title: "Flame Extinguishment Experiment",
    acronym: "FLEX",
    summary:
      "Studied fire suppression by burning liquid-fuel droplets while diluting the chamber atmosphere with carbon dioxide and helium, both of which suppress fire.",
    hardware: CIR_MDCA,
    fuel_classes: ["Liquid droplet"],
    topic_tags: ["Fire suppression", "Droplet combustion"],
    measurement_types: ["Droplet burning observation"],
    files: [placeholderFile("psi-flex", "FLEX investigation overview (placeholder)")],
  }),
  sample({
    id: "psi-flex-2",
    title: "Flame Extinguishment Experiment - 2",
    acronym: "FLEX-2",
    summary: "Second FLEX investigation featuring burning droplets of liquid fuel.",
    hardware: CIR_MDCA,
    fuel_classes: ["Liquid droplet"],
    topic_tags: ["Fire suppression", "Droplet combustion"],
  }),
  sample({
    id: "psi-cfi",
    title: "Cool Flames Investigation",
    acronym: "CFI",
    summary: "Burning liquid-fuel droplets studied with the droplet combustion apparatus.",
    hardware: CIR_MDCA,
    fuel_classes: ["Liquid droplet"],
    topic_tags: ["Droplet combustion"],
  }),
  sample({
    id: "psi-acme-bre",
    title: "Burning Rate Emulator (ACME)",
    acronym: "BRE",
    summary:
      "Part of the ACME project. Burned gaseous fuels, but was a study of materials flammability in still atmospheres as a function of material properties.",
    hardware: CIR_ACME,
    fuel_classes: ["Gas"],
    topic_tags: ["Material flammability"],
  }),
  sample({
    id: "psi-acme-efield",
    title: "Electric-Field Effects on Laminar Diffusion Flames (ACME)",
    acronym: "E-FIELD Flames",
    summary:
      "Part of the ACME project. Partial gravity was mimicked through the effect of an electric field on ions that naturally occur in flames.",
    environment: "Microgravity (electric field used to mimic partial-gravity effects)",
    hardware: CIR_ACME,
    fuel_classes: ["Gas"],
    topic_tags: ["Electric-field effects", "Flame structure"],
  }),
  sample({
    id: "psi-acme-cfig",
    title: "Cool Flames Investigation with Gases (ACME)",
    acronym: "CFI-G",
    summary:
      "Highest oxygen concentrations tested in microgravity. A nitrogen and flammable-gas mixture filled the chamber while an oxygen-nitrogen mixture flowed from a spherical burner, creating an inside-out flame.",
    hardware: CIR_ACME,
    fuel_classes: ["Gas"],
    fuel_materials: ["Propane (given as an example of the flammable gas)"],
    topic_tags: ["Oxygen & airflow effects", "Flame structure"],
    conditions: [
      {
        name: "Maximum oxygen concentration in oxidizer flow",
        value: 85,
        unit: "% O2",
        context: "Oxygen-nitrogen mixture flowing from the spherical burner",
        citation: challengeCitation("Objectives > Spacesuits and oxygen concentration"),
      },
    ],
  }),
  sample({
    id: "psi-spice",
    title: "Smoke Point In Co-flow Experiment",
    acronym: "SPICE",
    summary:
      "Studies flames of solid and gaseous fuels. Its modular fan-driven flow duct was reused by BASS, BASS-II and SLICE.",
    hardware: MSG_DUCT,
    fuel_classes: ["Solid", "Gas"],
    topic_tags: ["Flame structure", "Oxygen & airflow effects"],
  }),
  sample({
    id: "psi-slice",
    title: "Structure & Liftoff In Combustion Experiment",
    acronym: "SLICE",
    summary: "Studies flame structure and liftoff, conducted with the SPICE flow-duct hardware.",
    hardware: MSG_DUCT,
    fuel_classes: ["Gas"],
    topic_tags: ["Flame structure"],
  }),
];

export const FEATURED_IDS = ["psi-bass", "psi-flex", "psi-same", "psi-acme-cfig"];
