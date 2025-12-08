// src/lib/saveTerraformPlan.ts
import { doc, setDoc, getDoc, serverTimestamp } from "firebase/firestore";
import { db } from "./firebase";

export type TerraformValidation = {
  valid: boolean;
  errors?: string;
};

export type TerraformPlan = {
  user_id: string;
  terraformId: string;
  requirements: string;
  terraformCode: string;
  validation: TerraformValidation | null;
  status?: string;
  createdAt?: any;
  updatedAt?: any;
};

// Save or update a plan
export async function saveTerraformPlan(params: {
  user_id: string | null;
  terraformId: string;
  requirements: string;
  terraformCode: string;
  validation: TerraformValidation | null;
}) {
  const { user_id, terraformId, requirements, terraformCode, validation } =
    params;

  const ref = doc(db, "terraformPlans", terraformId);

  await setDoc(
    ref,
    {
      user_id,
      terraformId,
      requirements,
      terraformCode,
      validation: validation || null,
      status: validation?.valid ? "validated" : "generated",
      updatedAt: serverTimestamp(),
      createdAt: serverTimestamp(),
    },
    { merge: true }
  );
}

// Load a plan by id
export async function loadTerraformPlan(
  terraformId: string
): Promise<TerraformPlan | null> {
  const ref = doc(db, "terraformPlans", terraformId);
  const snap = await getDoc(ref);
  if (!snap.exists()) return null;

  const data = snap.data();

  return {
    user_id: data.userId,
    terraformId: data.terraformId,
    requirements: data.requirements,
    terraformCode: data.terraformCode,
    validation: (data.validation || null) as TerraformValidation | null,
    status: data.status,
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
  };
}
