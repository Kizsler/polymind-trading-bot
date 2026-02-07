-- Fix RLS policies for user_wallets and user_recommended_selections tables
-- Allow users to delete and update their own wallet entries

-- user_wallets table policies
DO $$
BEGIN
    -- Drop existing policies if they exist
    DROP POLICY IF EXISTS "Users can delete own wallets" ON user_wallets;
    DROP POLICY IF EXISTS "Users can update own wallets" ON user_wallets;
    DROP POLICY IF EXISTS "Users can insert own wallets" ON user_wallets;
    DROP POLICY IF EXISTS "Users can view own wallets" ON user_wallets;
EXCEPTION WHEN undefined_table THEN
    -- Table doesn't exist, skip
    NULL;
END $$;

-- Create policies for user_wallets
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_wallets') THEN
        -- Enable RLS if not already enabled
        ALTER TABLE user_wallets ENABLE ROW LEVEL SECURITY;

        -- Allow users to view their own wallets
        CREATE POLICY "Users can view own wallets" ON user_wallets
            FOR SELECT USING (auth.uid() = user_id);

        -- Allow users to insert their own wallets
        CREATE POLICY "Users can insert own wallets" ON user_wallets
            FOR INSERT WITH CHECK (auth.uid() = user_id);

        -- Allow users to update their own wallets
        CREATE POLICY "Users can update own wallets" ON user_wallets
            FOR UPDATE USING (auth.uid() = user_id);

        -- Allow users to delete their own wallets
        CREATE POLICY "Users can delete own wallets" ON user_wallets
            FOR DELETE USING (auth.uid() = user_id);
    END IF;
END $$;

-- user_recommended_selections table policies
DO $$
BEGIN
    -- Drop existing policies if they exist
    DROP POLICY IF EXISTS "Users can delete own selections" ON user_recommended_selections;
    DROP POLICY IF EXISTS "Users can update own selections" ON user_recommended_selections;
    DROP POLICY IF EXISTS "Users can insert own selections" ON user_recommended_selections;
    DROP POLICY IF EXISTS "Users can view own selections" ON user_recommended_selections;
EXCEPTION WHEN undefined_table THEN
    -- Table doesn't exist, skip
    NULL;
END $$;

-- Create policies for user_recommended_selections
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_recommended_selections') THEN
        -- Enable RLS if not already enabled
        ALTER TABLE user_recommended_selections ENABLE ROW LEVEL SECURITY;

        -- Allow users to view their own selections
        CREATE POLICY "Users can view own selections" ON user_recommended_selections
            FOR SELECT USING (auth.uid() = user_id);

        -- Allow users to insert their own selections
        CREATE POLICY "Users can insert own selections" ON user_recommended_selections
            FOR INSERT WITH CHECK (auth.uid() = user_id);

        -- Allow users to update their own selections
        CREATE POLICY "Users can update own selections" ON user_recommended_selections
            FOR UPDATE USING (auth.uid() = user_id);

        -- Allow users to delete their own selections
        CREATE POLICY "Users can delete own selections" ON user_recommended_selections
            FOR DELETE USING (auth.uid() = user_id);
    END IF;
END $$;
