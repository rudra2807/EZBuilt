// app/lib/saveConnection.ts
import {
  collection,
  addDoc,
  serverTimestamp,
  query,
  where,
  getDocs,
  limit,
  runTransaction,
  doc,
} from "firebase/firestore";
import { db } from "@/app/(app)/lib/firebase";

export type AwsConnection = {
  id: string;
  userId: string;
  externalId: string;
  roleArn: string;
};

export async function saveAwsConnection(params: {
  userId: string;
  externalId: string;
  roleArn: string;
}) {
  const { userId, externalId, roleArn } = params;
  const ref = doc(db, "awsConnections", params.userId);

  // await addDoc(collection(db, "awsConnections", userId), {
  //   userId,
  //   externalId,
  //   roleArn,
  //   updatedAt: serverTimestamp(),
  // });

  await runTransaction(db, async (tx) => {
    const snap = await tx.get(ref);

    if (snap.exists()) {
      throw new Error("AWS connection already exists for this user");
    }

    tx.set(ref, {
      userId,
      externalId,
      roleArn,
      createdAt: serverTimestamp(),
    });
  });
}

// New helper
export async function getAwsConnectionForUser(
  userId: string
): Promise<AwsConnection | null> {
  const q = query(
    collection(db, "awsConnections"),
    where("userId", "==", userId),
    limit(1)
  );

  const snap = await getDocs(q);
  if (snap.empty) return null;

  const doc = snap.docs[0];
  const data = doc.data();

  return {
    id: doc.id,
    userId: data.userId,
    externalId: data.externalId,
    roleArn: data.roleArn,
  };
}
